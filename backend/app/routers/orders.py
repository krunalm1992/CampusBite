from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import (
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusEvent,
    PaymentLedger,
    PaymentStatus,
    Restaurant,
    Review,
    User,
    UserRole,
)
from app.order_service import (
    ORDER_LOADS,
    apply_date_filters,
    assert_transition,
    detail_of,
    get_scoped_order,
    record_event,
    scoped_order_query,
    summary_list,
)
from app.schemas import AssignIn, OrderCreate, OrderDetail, PageOrders, ReviewIn, ReviewOut, StatusUpdate
from app.serializers import page_dict, review_out
from app.ws import manager

router = APIRouter(prefix="/api/orders", tags=["orders"])

STATUS_NOTE = {
    OrderStatus.PLACED.value: "Order placed",
    OrderStatus.ACCEPTED.value: "Kitchen accepted the order",
    OrderStatus.PREPARING.value: "Cooking started",
    OrderStatus.READY.value: "Packed and ready for a delivery partner",
    OrderStatus.ASSIGNED.value: "Delivery partner assigned",
    OrderStatus.OUT_FOR_DELIVERY.value: "Out for delivery",
    OrderStatus.DELIVERED.value: "Marked as delivered",
    OrderStatus.CANCELLED.value: "Cancelled by the customer",
    OrderStatus.REFUNDED.value: "Refund approved",
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _broadcast(order: Order, db: Session) -> None:
    owner_id = db.query(Restaurant.owner_id).filter(Restaurant.id == order.restaurant_id).scalar()
    ids = [order.customer_id, owner_id]
    if order.delivery_partner_id:
        ids.append(order.delivery_partner_id)
    await manager.send_many(
        ids,
        {
            "type": "order.updated",
            "order_id": order.id,
            "status": order.status,
            "message": f"Order #{order.id}: {STATUS_NOTE.get(order.status, 'Status updated')}",
        },
    )


@router.post("", response_model=OrderDetail, status_code=201)
async def place_order(
    body: OrderCreate,
    user: User = Depends(require_roles(UserRole.customer.value)),
    db: Session = Depends(get_db),
):
    restaurant = db.get(Restaurant, body.restaurant_id)
    if restaurant is None or not restaurant.is_active:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Prices come from the database. The client cannot set what it pays.
    requested = {line.menu_item_id: line.quantity for line in body.items}
    if len(requested) != len(body.items):
        raise HTTPException(status_code=400, detail="Each dish can only appear once in the order")
    dishes = db.query(MenuItem).filter(MenuItem.id.in_(requested)).all()
    found = {dish.id: dish for dish in dishes}
    missing = [item_id for item_id in requested if item_id not in found]
    if missing:
        raise HTTPException(status_code=400, detail="One or more dishes are not on this menu")
    for dish in dishes:
        if dish.restaurant_id != restaurant.id:
            raise HTTPException(status_code=400, detail="All dishes must come from the same restaurant")
        if not dish.is_available:
            raise HTTPException(status_code=400, detail=f"{dish.name} is unavailable")

    total = Decimal("0")
    lines: list[tuple[MenuItem, int]] = []
    for item_id, quantity in requested.items():
        dish = found[item_id]
        line_total = _money(dish.price * quantity)
        total += line_total
        lines.append((dish, quantity))
    total = _money(total)

    order = Order(
        customer_id=user.id,
        restaurant_id=restaurant.id,
        status=OrderStatus.PLACED.value,
        payment_status=PaymentStatus.mock_paid.value,
        total_amount=total,
        delivery_address=body.delivery_address.strip(),
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(order)
    db.flush()
    for dish, quantity in lines:
        db.add(
            OrderItem(
                order_id=order.id,
                menu_item_id=dish.id,
                item_name=dish.name,
                quantity=quantity,
                unit_price=dish.price,
                line_total=_money(dish.price * quantity),
            )
        )
    db.add(
        PaymentLedger(
            order_id=order.id,
            entry_type="charge",
            amount=total,
            status=PaymentStatus.mock_paid.value,
            note="Dummy payment captured when the order was placed",
        )
    )
    db.add(
        OrderStatusEvent(
            order_id=order.id,
            status=OrderStatus.PLACED.value,
            note="Order placed with a dummy payment",
            actor_id=user.id,
        )
    )
    db.commit()
    await _broadcast(order, db)
    return detail_of(get_scoped_order(db, user, order.id))


@router.get("", response_model=PageOrders)
def list_orders(
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    restaurant_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(8, ge=1, le=50),
    user: User = Depends(require_roles(UserRole.customer.value, UserRole.owner.value, UserRole.delivery.value)),
    db: Session = Depends(get_db),
):
    query = scoped_order_query(db, user)
    if status:
        query = query.filter(Order.status == status)
    if restaurant_id is not None:
        query = query.filter(Order.restaurant_id == restaurant_id)
    query = apply_date_filters(query, date_from, date_to)
    total = query.count()
    # selectinload is used for item/event collections so LIMIT is not multiplied
    # by a join. Many-to-one relations use joinedload and stay one row per order.
    rows = (
        query.options(*ORDER_LOADS)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return page_dict(summary_list(rows), total, page, page_size)


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(
    order_id: int,
    user: User = Depends(require_roles(UserRole.customer.value, UserRole.owner.value, UserRole.delivery.value)),
    db: Session = Depends(get_db),
):
    return detail_of(get_scoped_order(db, user, order_id))


@router.post("/{order_id}/status", response_model=OrderDetail)
async def update_status(
    order_id: int,
    body: StatusUpdate,
    user: User = Depends(require_roles(UserRole.customer.value, UserRole.owner.value, UserRole.delivery.value)),
    db: Session = Depends(get_db),
):
    order = get_scoped_order(db, user, order_id, for_update=True)
    assert_transition(order, body.status, user.role)
    # Delivery partners additionally have to be the person assigned to this order.
    # The scoped query already enforces that for the delivery role.
    record_event(db, order, body.status, STATUS_NOTE.get(body.status, "Status updated"), user.id)
    db.commit()
    await _broadcast(order, db)
    return detail_of(get_scoped_order(db, user, order.id))


@router.post("/{order_id}/assign", response_model=OrderDetail)
async def assign_partner(
    order_id: int,
    body: AssignIn,
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    order = get_scoped_order(db, user, order_id, for_update=True)
    if order.status != OrderStatus.READY.value:
        raise HTTPException(status_code=400, detail="A delivery partner can only be assigned when the order is READY")
    partner = db.get(User, body.delivery_partner_id)
    if partner is None or partner.role != UserRole.delivery.value or not partner.is_active:
        raise HTTPException(status_code=400, detail="Choose an active delivery partner")
    order.delivery_partner_id = partner.id
    record_event(db, order, OrderStatus.ASSIGNED.value, f"Assigned to {partner.full_name}", user.id)
    db.commit()
    await _broadcast(order, db)
    return detail_of(get_scoped_order(db, user, order.id))


@router.post("/{order_id}/review", response_model=ReviewOut, status_code=201)
def review_order(
    order_id: int,
    body: ReviewIn,
    user: User = Depends(require_roles(UserRole.customer.value)),
    db: Session = Depends(get_db),
):
    order = get_scoped_order(db, user, order_id, for_update=True)
    if order.status not in (OrderStatus.DELIVERED.value, OrderStatus.REFUNDED.value):
        raise HTTPException(status_code=400, detail="You can review an order after it is delivered")
    if db.query(Review).filter(Review.order_id == order.id).first():
        raise HTTPException(status_code=400, detail="This order already has a review")
    review = Review(
        order_id=order.id,
        customer_id=user.id,
        restaurant_id=order.restaurant_id,
        rating=body.rating,
        comment=body.comment.strip() if body.comment else None,
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="This order already has a review")
    db.refresh(review)
    return review_out(review, user.full_name)
