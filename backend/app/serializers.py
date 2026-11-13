"""Turn ORM rows into API shapes, including a few joined display fields."""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Order, ReminderLog, Restaurant, ReturnRequest, Review
from app.schemas import (
    OrderDetail,
    OrderItemOut,
    OrderSummary,
    PaymentOut,
    ReminderOut,
    RestaurantOut,
    ReturnOut,
    ReviewOut,
    StatusEventOut,
)


def money(value: Decimal | float | int) -> float:
    return float(value)


def review_out(review: Review | None, customer_name: str | None = None) -> ReviewOut | None:
    if review is None:
        return None
    return ReviewOut(
        id=review.id,
        order_id=review.order_id,
        customer_id=review.customer_id,
        restaurant_id=review.restaurant_id,
        customer_name=customer_name,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


def return_out(row: ReturnRequest | None, customer_name: str | None = None, restaurant_name: str | None = None) -> ReturnOut | None:
    if row is None:
        return None
    return ReturnOut(
        id=row.id,
        order_id=row.order_id,
        customer_id=row.customer_id,
        customer_name=customer_name,
        restaurant_name=restaurant_name,
        reason=row.reason,
        status=row.status,
        owner_note=row.owner_note,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


def order_summary(order: Order) -> OrderSummary:
    partner = order.delivery_partner
    return OrderSummary(
        id=order.id,
        status=order.status,
        payment_status=order.payment_status,
        total_amount=money(order.total_amount),
        delivery_address=order.delivery_address,
        notes=order.notes,
        created_at=order.created_at,
        updated_at=order.updated_at,
        customer_id=order.customer_id,
        customer_name=order.customer.full_name,
        customer_phone=order.customer.phone,
        restaurant_id=order.restaurant_id,
        restaurant_name=order.restaurant.name,
        restaurant_emoji=order.restaurant.emoji,
        delivery_partner_id=order.delivery_partner_id,
        delivery_partner_name=partner.full_name if partner else None,
        items=[
            OrderItemOut(
                id=item.id,
                menu_item_id=item.menu_item_id,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=money(item.unit_price),
                line_total=money(item.line_total),
            )
            for item in order.items
        ],
        review=review_out(order.review, order.customer.full_name),
        return_request=return_out(order.return_request, order.customer.full_name, order.restaurant.name),
    )


def order_detail(order: Order) -> OrderDetail:
    summary = order_summary(order)
    events = sorted(order.events, key=lambda event: event.created_at)
    payments = sorted(order.payments, key=lambda payment: payment.created_at)
    return OrderDetail(
        **summary.model_dump(),
        events=[
            StatusEventOut(id=event.id, status=event.status, note=event.note, created_at=event.created_at)
            for event in events
        ],
        payments=[
            PaymentOut(
                id=payment.id,
                entry_type=payment.entry_type,
                amount=money(payment.amount),
                status=payment.status,
                note=payment.note,
                created_at=payment.created_at,
            )
            for payment in payments
        ],
    )


def restaurant_ratings(db: Session, restaurant_ids: list[int]) -> dict[int, tuple[float | None, int]]:
    if not restaurant_ids:
        return {}
    rows = (
        db.query(Review.restaurant_id, func.avg(Review.rating), func.count(Review.id))
        .filter(Review.restaurant_id.in_(restaurant_ids))
        .group_by(Review.restaurant_id)
        .all()
    )
    found = {rid: (round(float(avg), 1), count) for rid, avg, count in rows}
    return {rid: found.get(rid, (None, 0)) for rid in restaurant_ids}


def restaurant_out(restaurant: Restaurant, rating: float | None, review_count: int) -> RestaurantOut:
    owner = restaurant.owner
    return RestaurantOut(
        id=restaurant.id,
        owner_id=restaurant.owner_id,
        owner_name=owner.full_name if owner else None,
        name=restaurant.name,
        description=restaurant.description,
        cuisine=restaurant.cuisine,
        address=restaurant.address,
        phone=restaurant.phone,
        emoji=restaurant.emoji,
        is_active=restaurant.is_active,
        rating=rating,
        review_count=review_count,
    )


def reminder_out(row: ReminderLog) -> ReminderOut:
    return ReminderOut(
        id=row.id,
        order_id=row.order_id,
        restaurant_id=row.restaurant_id,
        restaurant_name=row.order.restaurant.name,
        message=row.message,
        is_read=row.is_read,
        created_at=row.created_at,
    )


def page_dict(items, total: int, page: int, page_size: int) -> dict:
    pages = (total + page_size - 1) // page_size if total else 0
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}
