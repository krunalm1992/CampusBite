from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_roles
from app.models import (
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
    ReminderLog,
    Restaurant,
    Review,
    User,
    UserRole,
)
from app.order_service import ACTIVE_STATUSES, owner_restaurant_ids
from app.schemas import DishStat, PageReminders, PartnerOut, RestaurantOut, StatsOut
from app.serializers import page_dict, reminder_out, restaurant_out, restaurant_ratings

router = APIRouter(prefix="/api/owner", tags=["owner"])


@router.get("/restaurants", response_model=list[RestaurantOut])
def my_restaurants(
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Restaurant)
        .options(joinedload(Restaurant.owner))
        .filter(Restaurant.owner_id == user.id)
        .order_by(Restaurant.name)
        .all()
    )
    ratings = restaurant_ratings(db, [row.id for row in rows])
    return [restaurant_out(row, *ratings[row.id]) for row in rows]


@router.get("/stats", response_model=StatsOut)
def stats(
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    ids = owner_restaurant_ids(db, user)
    empty = StatsOut(
        restaurant_count=len(ids),
        total_orders=0,
        active_orders=0,
        orders_today=0,
        revenue=0,
        average_rating=None,
        review_count=0,
        unread_reminders=0,
        top_dishes=[],
        orders_by_status={},
    )
    if not ids:
        return empty
    base = db.query(Order).filter(Order.restaurant_id.in_(ids))
    start_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    revenue = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            Order.restaurant_id.in_(ids),
            Order.payment_status == PaymentStatus.mock_paid.value,
            Order.status != OrderStatus.CANCELLED.value,
        )
        .scalar()
    )
    avg, review_count = (
        db.query(func.avg(Review.rating), func.count(Review.id)).filter(Review.restaurant_id.in_(ids)).one()
    )
    status_rows = (
        db.query(Order.status, func.count(Order.id)).filter(Order.restaurant_id.in_(ids)).group_by(Order.status).all()
    )
    top_rows = (
        db.query(OrderItem.item_name, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.restaurant_id.in_(ids), Order.status != OrderStatus.CANCELLED.value)
        .group_by(OrderItem.item_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    unread = (
        db.query(ReminderLog)
        .filter(ReminderLog.restaurant_id.in_(ids), ReminderLog.is_read.is_(False))
        .count()
    )
    return StatsOut(
        restaurant_count=len(ids),
        total_orders=base.count(),
        active_orders=base.filter(Order.status.in_(ACTIVE_STATUSES)).count(),
        orders_today=base.filter(Order.created_at >= start_today).count(),
        revenue=float(revenue or 0),
        average_rating=round(float(avg), 1) if avg is not None else None,
        review_count=review_count,
        unread_reminders=unread,
        top_dishes=[DishStat(name=name, quantity=int(qty)) for name, qty in top_rows],
        orders_by_status={status: count for status, count in status_rows},
    )


@router.get("/reminders", response_model=PageReminders)
def reminders(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    ids = owner_restaurant_ids(db, user)
    query = (
        db.query(ReminderLog)
        .options(joinedload(ReminderLog.order).joinedload(Order.restaurant))
        .filter(ReminderLog.restaurant_id.in_(ids or [-1]))
    )
    if unread_only:
        query = query.filter(ReminderLog.is_read.is_(False))
    total = query.count()
    rows = query.order_by(ReminderLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_dict([reminder_out(row) for row in rows], total, page, page_size)


@router.post("/reminders/{reminder_id}/read", response_model=dict)
def mark_read(
    reminder_id: int,
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    ids = owner_restaurant_ids(db, user)
    row = db.get(ReminderLog, reminder_id)
    if row is None or row.restaurant_id not in ids:
        raise HTTPException(status_code=404, detail="Reminder not found")
    row.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/reminders/read-all", response_model=dict)
def mark_all_read(
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    ids = owner_restaurant_ids(db, user)
    (
        db.query(ReminderLog)
        .filter(ReminderLog.restaurant_id.in_(ids or [-1]), ReminderLog.is_read.is_(False))
        .update({ReminderLog.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return {"ok": True}


@router.get("/partners", response_model=list[PartnerOut])
def partners(
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(User)
        .filter(User.role == UserRole.delivery.value, User.is_active.is_(True))
        .order_by(User.full_name)
        .all()
    )
    return [PartnerOut(id=row.id, full_name=row.full_name, phone=row.phone) for row in rows]
