"""Shared helpers for order reads and the status machine.

Invalid jumps are rejected here so every router follows the same rules.
"""

from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Order, OrderStatus, OrderStatusEvent, Restaurant, User, UserRole
from app.serializers import order_detail, order_summary

# Only the next legal step is allowed. ASSIGNED is handled by the assign endpoint,
# because it also has to record which delivery partner took the order.
TRANSITIONS: dict[tuple[str, str], str] = {
    (OrderStatus.PLACED.value, OrderStatus.CANCELLED.value): UserRole.customer.value,
    (OrderStatus.PLACED.value, OrderStatus.ACCEPTED.value): UserRole.owner.value,
    (OrderStatus.ACCEPTED.value, OrderStatus.PREPARING.value): UserRole.owner.value,
    (OrderStatus.PREPARING.value, OrderStatus.READY.value): UserRole.owner.value,
    (OrderStatus.ASSIGNED.value, OrderStatus.OUT_FOR_DELIVERY.value): UserRole.delivery.value,
    (OrderStatus.OUT_FOR_DELIVERY.value, OrderStatus.DELIVERED.value): UserRole.delivery.value,
}

ACTIVE_STATUSES = {
    OrderStatus.PLACED.value,
    OrderStatus.ACCEPTED.value,
    OrderStatus.PREPARING.value,
    OrderStatus.READY.value,
    OrderStatus.ASSIGNED.value,
    OrderStatus.OUT_FOR_DELIVERY.value,
}

ORDER_LOADS = (
    selectinload(Order.items),
    selectinload(Order.events),
    selectinload(Order.payments),
    joinedload(Order.review),
    joinedload(Order.return_request),
    joinedload(Order.customer),
    joinedload(Order.restaurant),
    joinedload(Order.delivery_partner),
)


def owner_restaurant_ids(db: Session, user: User) -> list[int]:
    rows = db.query(Restaurant.id).filter(Restaurant.owner_id == user.id).all()
    return [row[0] for row in rows]


def scoped_order_query(db: Session, user: User):
    """Each role only sees orders they are allowed to touch."""
    query = db.query(Order)
    if user.role == UserRole.customer.value:
        return query.filter(Order.customer_id == user.id)
    if user.role == UserRole.owner.value:
        ids = owner_restaurant_ids(db, user)
        return query.filter(Order.restaurant_id.in_(ids or [-1]))
    if user.role == UserRole.delivery.value:
        return query.filter(Order.delivery_partner_id == user.id)
    raise HTTPException(status_code=403, detail="You do not have access to orders")


def get_scoped_order(db: Session, user: User, order_id: int, *, for_update: bool = False) -> Order:
    query = scoped_order_query(db, user).filter(Order.id == order_id)
    if for_update:
        # Lock only the order row. Eager joins plus FOR UPDATE fail on PostgreSQL
        # when optional relations (review, return) are outer-joined.
        order = query.with_for_update().first()
    else:
        order = query.options(*ORDER_LOADS).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def apply_date_filters(query, date_from: str | None, date_to: str | None):
    try:
        if date_from:
            start = datetime.combine(datetime.fromisoformat(date_from).date(), time.min, tzinfo=timezone.utc)
            query = query.filter(Order.created_at >= start)
        if date_to:
            # Inclusive end date: anything created before the next midnight UTC.
            end = datetime.combine(datetime.fromisoformat(date_to).date(), time.min, tzinfo=timezone.utc) + timedelta(days=1)
            query = query.filter(Order.created_at < end)
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must use the YYYY-MM-DD format")
    return query


def record_event(db: Session, order: Order, status: str, note: str, actor_id: int | None) -> None:
    order.status = status
    order.updated_at = datetime.now(timezone.utc)
    db.add(OrderStatusEvent(order_id=order.id, status=status, note=note, actor_id=actor_id))


def assert_transition(order: Order, new_status: str, role: str) -> None:
    expected_role = TRANSITIONS.get((order.status, new_status))
    if expected_role is None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move an order from {order.status} to {new_status}",
        )
    if role != expected_role:
        raise HTTPException(status_code=403, detail="Your role cannot make this status change")


def notify_ids(order: Order) -> list[int]:
    ids = [order.customer_id, order.restaurant.owner_id]
    if order.delivery_partner_id:
        ids.append(order.delivery_partner_id)
    return ids


def summary_list(orders: list[Order]):
    return [order_summary(order) for order in orders]


def detail_of(order: Order):
    return order_detail(order)
