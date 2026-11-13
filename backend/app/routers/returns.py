from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_roles
from app.models import (
    Order,
    OrderStatus,
    PaymentLedger,
    PaymentStatus,
    Restaurant,
    ReturnRequest,
    ReturnStatus,
    User,
    UserRole,
)
from app.order_service import get_scoped_order, record_event
from app.schemas import PageReturns, ReturnDecision, ReturnIn, ReturnOut
from app.serializers import page_dict, return_out
from app.ws import manager

router = APIRouter(prefix="/api/returns", tags=["returns"])


def _return_query(db: Session, user: User):
    query = (
        db.query(ReturnRequest)
        .join(Order, Order.id == ReturnRequest.order_id)
        .options(joinedload(ReturnRequest.order).joinedload(Order.customer), joinedload(ReturnRequest.order).joinedload(Order.restaurant))
    )
    if user.role == UserRole.customer.value:
        return query.filter(ReturnRequest.customer_id == user.id)
    if user.role == UserRole.owner.value:
        ids = [row[0] for row in db.query(Restaurant.id).filter(Restaurant.owner_id == user.id).all()]
        return query.filter(Order.restaurant_id.in_(ids or [-1]))
    raise HTTPException(status_code=403, detail="You do not have access to return requests")


def _as_out(row: ReturnRequest) -> ReturnOut:
    payload = return_out(row, row.order.customer.full_name, row.order.restaurant.name)
    assert payload is not None
    return payload


@router.get("", response_model=PageReturns)
def list_returns(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: User = Depends(require_roles(UserRole.customer.value, UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    query = _return_query(db, user)
    if status:
        query = query.filter(ReturnRequest.status == status)
    total = query.count()
    rows = query.order_by(ReturnRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_dict([_as_out(row) for row in rows], total, page, page_size)


@router.post("/orders/{order_id}", response_model=ReturnOut, status_code=201)
async def request_return(
    order_id: int,
    body: ReturnIn,
    user: User = Depends(require_roles(UserRole.customer.value)),
    db: Session = Depends(get_db),
):
    order = get_scoped_order(db, user, order_id, for_update=True)
    # Refunds are only for food that actually arrived. Cancel covers PLACED orders.
    if order.status != OrderStatus.DELIVERED.value:
        raise HTTPException(status_code=400, detail="You can request a return only after the order is delivered")
    if order.return_request is not None or db.query(ReturnRequest).filter(ReturnRequest.order_id == order.id).first():
        raise HTTPException(status_code=400, detail="A return request already exists for this order")
    row = ReturnRequest(order_id=order.id, customer_id=user.id, reason=body.reason.strip(), status=ReturnStatus.pending.value)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A return request already exists for this order")
    db.refresh(row)
    owner_id = db.query(Restaurant.owner_id).filter(Restaurant.id == order.restaurant_id).scalar()
    await manager.send_many(
        [owner_id, user.id],
        {
            "type": "return.updated",
            "order_id": order.id,
            "message": f"Return requested for order #{order.id}",
        },
    )
    loaded = db.query(ReturnRequest).options(
        joinedload(ReturnRequest.order).joinedload(Order.customer),
        joinedload(ReturnRequest.order).joinedload(Order.restaurant),
    ).filter(ReturnRequest.id == row.id).one()
    return _as_out(loaded)


@router.post("/{return_id}/decision", response_model=ReturnOut)
async def decide_return(
    return_id: int,
    body: ReturnDecision,
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    row = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Return request not found")
    order = db.query(Order).filter(Order.id == row.order_id).with_for_update().one()
    restaurant = db.get(Restaurant, order.restaurant_id)
    if restaurant is None or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Return request not found")
    if row.status != ReturnStatus.pending.value:
        raise HTTPException(status_code=400, detail="This return request has already been decided")

    row.owner_note = body.note.strip() if body.note else None
    row.resolved_at = datetime.now(timezone.utc)
    if body.action == "approve":
        row.status = ReturnStatus.approved.value
        order.payment_status = PaymentStatus.refunded.value
        db.add(
            PaymentLedger(
                order_id=order.id,
                entry_type="refund",
                amount=order.total_amount,
                status=PaymentStatus.refunded.value,
                note=row.owner_note or "Refund approved by the restaurant",
            )
        )
        record_event(db, order, OrderStatus.REFUNDED.value, "Refund approved", user.id)
        message = f"Refund approved for order #{order.id}"
    else:
        row.status = ReturnStatus.rejected.value
        message = f"Return request rejected for order #{order.id}"

    db.commit()
    owner_id = user.id
    await manager.send_many(
        [order.customer_id, owner_id],
        {"type": "return.updated", "order_id": order.id, "status": row.status, "message": message},
    )
    loaded = db.query(ReturnRequest).options(
        joinedload(ReturnRequest.order).joinedload(Order.customer),
        joinedload(ReturnRequest.order).joinedload(Order.restaurant),
    ).filter(ReturnRequest.id == row.id).one()
    return _as_out(loaded)
