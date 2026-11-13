"""Background scan for orders the kitchen has not touched in time.

Real-time push is optional here. The reminder row is what the owner dashboard
reads, and a socket event is sent as well when the owner happens to be online.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models import Order, OrderStatus, ReminderLog
from app.ws import manager

logger = logging.getLogger("campusbite.reminders")

WATCHED = (OrderStatus.PLACED.value, OrderStatus.ACCEPTED.value)


def create_reminders() -> list[tuple[int, dict]]:
    """Return (owner_id, payload) for each new reminder row."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.reminder_stale_minutes)
    created: list[tuple[int, dict]] = []
    db = SessionLocal()
    try:
        stale_orders = (
            db.query(Order)
            .options(joinedload(Order.restaurant))
            .filter(Order.status.in_(WATCHED), Order.updated_at < cutoff)
            .all()
        )
        for order in stale_orders:
            already = (
                db.query(ReminderLog)
                .filter(ReminderLog.order_id == order.id, ReminderLog.is_read.is_(False))
                .first()
            )
            # One unread reminder per order. A new one is written after the owner
            # marks the previous reminder read and the order is still stale.
            if already:
                continue
            message = (
                f"Order #{order.id} is still {order.status} and has not been updated "
                f"for over {settings.reminder_stale_minutes} minutes."
            )
            row = ReminderLog(order_id=order.id, restaurant_id=order.restaurant_id, message=message)
            db.add(row)
            db.flush()
            created.append(
                (
                    order.restaurant.owner_id,
                    {
                        "type": "reminder.created",
                        "order_id": order.id,
                        "reminder_id": row.id,
                        "message": message,
                    },
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return created


async def reminder_loop() -> None:
    # Give the app a moment to finish startup and seeding.
    await asyncio.sleep(5)
    while True:
        try:
            created = await asyncio.to_thread(create_reminders)
            for owner_id, payload in created:
                await manager.send_many([owner_id], payload)
            if created:
                logger.info("Created %s order reminder(s)", len(created))
        except Exception:
            logger.exception("Reminder scan failed")
        await asyncio.sleep(settings.reminder_interval_seconds)
