"""Customer order insights.

The model only ever sees the authenticated customer's own orders. There is no
way to pass another user id into this router.
"""

import json
import logging
import threading
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings
from app.database import get_db
from app.deps import require_roles
from app.models import Order, OrderStatus, User, UserRole
from app.schemas import DishStat, InsightIn, InsightOut, SnapshotOrder, SnapshotOut

router = APIRouter(prefix="/api/ai", tags=["insights"])
logger = logging.getLogger("campusbite.ai")

_hits: dict[int, list[float]] = {}
_lock = threading.Lock()

CLOSED = {OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value, OrderStatus.REFUNDED.value}

SYSTEM_PROMPT = (
    "You are CampusBite's order assistant for one student. "
    "Answer using only the JSON order history in the user message. "
    "If the history does not contain the answer, say so. "
    "Do not invent orders, items, restaurants, or amounts. "
    "Use Indian Rupees (₹). Be concise."
)


def _limit(user_id: int) -> None:
    now = time.monotonic()
    with _lock:
        recent = [stamp for stamp in _hits.get(user_id, []) if now - stamp < 60]
        if len(recent) >= settings.ai_requests_per_minute:
            raise HTTPException(status_code=429, detail="Too many insight requests. Please wait a minute and try again.")
        recent.append(now)
        _hits[user_id] = recent


def _history(db: Session, user: User) -> list[dict]:
    orders = (
        db.query(Order)
        .options(selectinload(Order.items), joinedload(Order.restaurant))
        .filter(Order.customer_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(30)
        .all()
    )
    history = []
    for order in orders:
        history.append(
            {
                "id": order.id,
                "restaurant": order.restaurant.name,
                "status": order.status,
                "payment_status": order.payment_status,
                "total": float(order.total_amount),
                "created_at": order.created_at.isoformat(),
                "items": [
                    {"name": item.item_name, "quantity": item.quantity, "line_total": float(item.line_total)}
                    for item in order.items
                ],
            }
        )
    return history


def _snapshot(history: list[dict]) -> SnapshotOut:
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    open_orders = [row for row in history if row["status"] not in CLOSED]
    spend = 0.0
    counts: Counter[str] = Counter()
    for row in history:
        created = datetime.fromisoformat(row["created_at"])
        if created >= week_ago and row["status"] != OrderStatus.CANCELLED.value:
            spend += row["total"]
        for item in row["items"]:
            counts[item["name"]] += item["quantity"]
    def brief(row: dict) -> SnapshotOrder:
        return SnapshotOrder(
            id=row["id"],
            restaurant=row["restaurant"],
            status=row["status"],
            total_amount=row["total"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
    top = [DishStat(name=name, quantity=qty) for name, qty in counts.most_common(5)]
    return SnapshotOut(
        order_count=len(history),
        open_count=len(open_orders),
        spend_this_week=round(spend, 2),
        top_items=top,
        last_five=[brief(row) for row in history[:5]],
        open_orders=[brief(row) for row in open_orders],
    )


def _local_answer(question: str, history: list[dict]) -> str:
    """Used only when OPENAI_API_KEY is empty, so the demo still answers."""
    question_l = question.lower()
    if not history:
        return "You have not placed any orders yet."
    if any(word in question_l for word in ("not delivered", "undelivered", "still", "pending", "open")):
        open_orders = [row for row in history if row["status"] not in CLOSED]
        if not open_orders:
            body = "Every order in your history is delivered, cancelled, or refunded."
        else:
            bits = [f"#{row['id']} from {row['restaurant']} ({row['status']}, ₹{row['total']:.0f})" for row in open_orders]
            body = "These orders are not delivered yet: " + "; ".join(bits) + "."
    elif any(word in question_l for word in ("spend", "spent", "week", "cost", "rupee")):
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        spend = sum(
            row["total"]
            for row in history
            if datetime.fromisoformat(row["created_at"]) >= week_ago and row["status"] != OrderStatus.CANCELLED.value
        )
        body = f"In the last 7 days you spent ₹{spend:.0f}, excluding cancelled orders."
    elif any(word in question_l for word in ("frequent", "most", "often", "favourite", "favorite")):
        counts: Counter[str] = Counter()
        for row in history:
            for item in row["items"]:
                counts[item["name"]] += item["quantity"]
        if not counts:
            body = "There are no dishes in your order history yet."
        else:
            top = ", ".join(f"{name} ×{qty}" for name, qty in counts.most_common(3))
            body = f"You have ordered these most often: {top}."
    else:
        bits = []
        for row in history[:5]:
            names = ", ".join(item["name"] for item in row["items"])
            bits.append(f"#{row['id']} at {row['restaurant']} ({row['status']}, ₹{row['total']:.0f}): {names}")
        body = "Here are your last five orders. " + " ".join(bits)
    return (
        "OpenAI is not configured, so this was calculated directly from your own orders. "
        + body
    )


async def _ask_openai(question: str, history: list[dict]) -> str:
    payload = {
        "model": settings.openai_model,
        "temperature": 0.2,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current time (UTC): {datetime.now(timezone.utc).isoformat()}\n\n"
                    f"Order history JSON:\n{json.dumps(history)}\n\n"
                    f"Question: {question}"
                ),
            },
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        logger.warning("OpenAI timeout: %s", exc)
        raise HTTPException(status_code=504, detail="The insights service timed out. Try again in a moment.") from exc
    except httpx.HTTPError as exc:
        logger.warning("OpenAI connection error: %s", exc)
        raise HTTPException(status_code=502, detail="The insights service could not be reached.") from exc

    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="The insights service is busy. Try again shortly.")
    if response.status_code >= 400:
        # Log the body for the operator, but do not return it. It can echo request details.
        logger.warning("OpenAI error %s", response.status_code)
        raise HTTPException(status_code=502, detail="The insights service returned an error.")
    try:
        return response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("Unexpected OpenAI payload: %s", exc)
        raise HTTPException(status_code=502, detail="The insights service returned an unexpected response.") from exc


@router.get("/snapshot", response_model=SnapshotOut)
def snapshot(
    user: User = Depends(require_roles(UserRole.customer.value)),
    db: Session = Depends(get_db),
):
    return _snapshot(_history(db, user))


@router.post("/insights", response_model=InsightOut)
async def insights(
    body: InsightIn,
    user: User = Depends(require_roles(UserRole.customer.value)),
    db: Session = Depends(get_db),
):
    _limit(user.id)
    history = _history(db, user)
    if not settings.openai_api_key.strip():
        return InsightOut(answer=_local_answer(body.question.strip(), history), source="local")
    answer = await _ask_openai(body.question.strip(), history)
    return InsightOut(answer=answer, source="openai")
