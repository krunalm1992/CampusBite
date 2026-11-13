"""Demo data so the app is usable immediately after Docker Compose starts.

Passwords below are local demo credentials, not production secrets.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusEvent,
    PaymentLedger,
    PaymentStatus,
    ReminderLog,
    Restaurant,
    Review,
    User,
    UserRole,
)
from app.security import hash_password

DEMO_PASSWORD = {
    "admin": "Admin@123",
    "owner": "Owner@123",
    "delivery": "Delivery@123",
    "customer": "Customer@123",
}


def _user(db: Session, name: str, email: str, phone: str, role: str, password: str) -> User:
    user = User(
        full_name=name,
        email=email.lower(),
        phone=phone,
        role=role,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _restaurant(db: Session, owner: User, name: str, cuisine: str, description: str, address: str, phone: str, emoji: str) -> Restaurant:
    row = Restaurant(
        owner_id=owner.id,
        name=name,
        cuisine=cuisine,
        description=description,
        address=address,
        phone=phone,
        emoji=emoji,
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def _dish(db: Session, restaurant: Restaurant, name: str, category: str, price: str, description: str, emoji: str) -> MenuItem:
    row = MenuItem(
        restaurant_id=restaurant.id,
        name=name,
        category=category,
        price=Decimal(price),
        description=description,
        emoji=emoji,
        is_available=True,
    )
    db.add(row)
    db.flush()
    return row


def _order(
    db: Session,
    *,
    customer: User,
    restaurant: Restaurant,
    partner: User | None,
    status: str,
    address: str,
    notes: str | None,
    lines: list[tuple[MenuItem, int]],
    created_at: datetime,
    updated_at: datetime,
    events: list[tuple[str, str, datetime]],
) -> Order:
    total = sum((item.price * qty for item, qty in lines), Decimal("0"))
    order = Order(
        customer_id=customer.id,
        restaurant_id=restaurant.id,
        delivery_partner_id=partner.id if partner else None,
        status=status,
        payment_status=PaymentStatus.mock_paid.value,
        total_amount=total,
        delivery_address=address,
        notes=notes,
        created_at=created_at,
        updated_at=updated_at,
    )
    db.add(order)
    db.flush()
    for item, qty in lines:
        db.add(
            OrderItem(
                order_id=order.id,
                menu_item_id=item.id,
                item_name=item.name,
                quantity=qty,
                unit_price=item.price,
                line_total=item.price * qty,
            )
        )
    db.add(
        PaymentLedger(
            order_id=order.id,
            entry_type="charge",
            amount=total,
            status=PaymentStatus.mock_paid.value,
            note="Dummy payment captured when the order was placed",
            created_at=created_at,
        )
    )
    for status_name, note, at in events:
        db.add(
            OrderStatusEvent(
                order_id=order.id,
                status=status_name,
                note=note,
                actor_id=customer.id,
                created_at=at,
            )
        )
    return order


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return

    admin = _user(db, "Campus Admin", "admin@campusbite.com", "9000000001", UserRole.admin.value, DEMO_PASSWORD["admin"])
    owner = _user(db, "Ananya Shah", "owner@campusbite.com", "9000000002", UserRole.owner.value, DEMO_PASSWORD["owner"])
    owner_two = _user(db, "Vikram Rao", "owner2@campusbite.com", "9000000003", UserRole.owner.value, DEMO_PASSWORD["owner"])
    rahul = _user(db, "Rahul More", "delivery@campusbite.com", "9000000004", UserRole.delivery.value, DEMO_PASSWORD["delivery"])
    sana = _user(db, "Sana Iqbal", "sana.delivery@campusbite.com", "9000000005", UserRole.delivery.value, DEMO_PASSWORD["delivery"])
    aisha = _user(db, "Aisha Khan", "customer@campusbite.com", "9000000006", UserRole.customer.value, DEMO_PASSWORD["customer"])

    north = _restaurant(
        db, owner, "North Court Mess", "North Indian",
        "Hostel favourite for thalis, biryani, and chai that actually tastes like home.",
        "Hostel 4 lane, Campus North", "9800001001", "🍛",
    )
    cafe = _restaurant(
        db, owner, "Library Lawn Cafe", "Cafe",
        "Sandwiches and filter coffee for the long stretch between lectures.",
        "Central Library lawn", "9800001002", "☕",
    )
    burger = _restaurant(
        db, owner_two, "The Byte Burger", "Burgers",
        "Stacked burgers and fries from the student center counter.",
        "Student Center, Ground floor", "9800001003", "🍔",
    )
    noodles = _restaurant(
        db, owner_two, "Noodle Window", "Asian",
        "Wok-fired noodles and momos served from Block C food street.",
        "Block C food street", "9800001004", "🍜",
    )

    thali = _dish(db, north, "Veg Thali", "Mains", "120", "Dal, sabzi, rice, roti, and salad.", "🍛")
    biryani = _dish(db, north, "Chicken Biryani", "Mains", "180", "Slow-cooked rice with campus-style chicken.", "🍗")
    paneer = _dish(db, north, "Paneer Butter Masala", "Mains", "150", "Creamy tomato gravy, best with roti.", "🧀")
    dal = _dish(db, north, "Dal Tadka", "Mains", "90", "Yellow dal with a garlic tadka.", "🥣")
    chai = _dish(db, north, "Masala Chai", "Drinks", "20", "Strong ginger chai in a glass.", "🍵")
    jamun = _dish(db, north, "Gulab Jamun", "Desserts", "40", "Two pieces, warm syrup.", "🍩")

    classic = _dish(db, burger, "Classic Campus Burger", "Mains", "140", "Patty, cheese, and the usual crunch.", "🍔")
    paneer_stack = _dish(db, burger, "Paneer Stack", "Mains", "150", "Grilled paneer, mint mayo, and lettuce.", "🥬")
    fries = _dish(db, burger, "Peri Peri Fries", "Sides", "80", "Salted fries with peri peri dust.", "🍟")
    cold_coffee = _dish(db, burger, "Cold Coffee", "Drinks", "70", "Blended coffee with a little chocolate.", "🥤")
    brownie = _dish(db, burger, "Chocolate Brownie", "Desserts", "90", "Warm brownie, no ice cream.", "🍫")

    hakka = _dish(db, noodles, "Veg Hakka Noodles", "Mains", "110", "Cabbage, pepper, and a hot wok.", "🍜")
    chicken_noodles = _dish(db, noodles, "Chicken Noodles", "Mains", "140", "Same wok, with shredded chicken.", "🍝")
    momos = _dish(db, noodles, "Steamed Momos", "Snacks", "80", "Eight vegetable momos and chutney.", "🥟")
    chilli = _dish(db, noodles, "Chilli Paneer", "Mains", "130", "Crispy paneer, onion, and soy glaze.", "🌶️")
    iced_tea = _dish(db, noodles, "Iced Tea", "Drinks", "50", "Lemon iced tea.", "🧊")

    filter_coffee = _dish(db, cafe, "Filter Coffee", "Drinks", "40", "Decoction and hot milk.", "☕")
    cappuccino = _dish(db, cafe, "Cappuccino", "Drinks", "80", "Espresso with a thick foam cap.", "☕")
    sandwich = _dish(db, cafe, "Veg Sandwich", "Snacks", "70", "Toasted, with mint chutney.", "🥪")
    muffin = _dish(db, cafe, "Chocolate Muffin", "Desserts", "60", "Baked this morning.", "🧁")
    fruit = _dish(db, cafe, "Fruit Bowl", "Snacks", "90", "Seasonal fruit, cut to order.", "🍓")

    now = datetime.now(timezone.utc)
    address = "Hostel 4, Room 212, Campus North"

    delivered_review = _order(
        db,
        customer=aisha,
        restaurant=north,
        partner=rahul,
        status=OrderStatus.DELIVERED.value,
        address=address,
        notes="Less spicy, please.",
        lines=[(thali, 1), (chai, 2)],
        created_at=now - timedelta(days=6, hours=3),
        updated_at=now - timedelta(days=6, hours=2),
        events=[
            (OrderStatus.PLACED.value, "Order placed", now - timedelta(days=6, hours=3)),
            (OrderStatus.ACCEPTED.value, "Kitchen accepted the order", now - timedelta(days=6, hours=3) + timedelta(minutes=4)),
            (OrderStatus.PREPARING.value, "Cooking started", now - timedelta(days=6, hours=3) + timedelta(minutes=8)),
            (OrderStatus.READY.value, "Packed and ready", now - timedelta(days=6, hours=2, minutes=20)),
            (OrderStatus.ASSIGNED.value, "Assigned to Rahul More", now - timedelta(days=6, hours=2, minutes=15)),
            (OrderStatus.OUT_FOR_DELIVERY.value, "Out for delivery", now - timedelta(days=6, hours=2, minutes=10)),
            (OrderStatus.DELIVERED.value, "Delivered to the hostel", now - timedelta(days=6, hours=2)),
        ],
    )
    db.add(
        Review(
            order_id=delivered_review.id,
            customer_id=aisha.id,
            restaurant_id=north.id,
            rating=5,
            comment="Thali was hot and the chai was perfect after lab.",
            created_at=now - timedelta(days=6, hours=1),
        )
    )

    _order(
        db,
        customer=aisha,
        restaurant=burger,
        partner=sana,
        status=OrderStatus.DELIVERED.value,
        address=address,
        notes=None,
        lines=[(classic, 1), (fries, 1)],
        created_at=now - timedelta(days=3, hours=5),
        updated_at=now - timedelta(days=3, hours=4),
        events=[
            (OrderStatus.PLACED.value, "Order placed", now - timedelta(days=3, hours=5)),
            (OrderStatus.ACCEPTED.value, "Kitchen accepted the order", now - timedelta(days=3, hours=5) + timedelta(minutes=3)),
            (OrderStatus.PREPARING.value, "Cooking started", now - timedelta(days=3, hours=4, minutes=40)),
            (OrderStatus.READY.value, "Packed and ready", now - timedelta(days=3, hours=4, minutes=20)),
            (OrderStatus.ASSIGNED.value, "Assigned to Sana Iqbal", now - timedelta(days=3, hours=4, minutes=18)),
            (OrderStatus.OUT_FOR_DELIVERY.value, "Out for delivery", now - timedelta(days=3, hours=4, minutes=12)),
            (OrderStatus.DELIVERED.value, "Delivered", now - timedelta(days=3, hours=4)),
        ],
    )

    _order(
        db,
        customer=aisha,
        restaurant=noodles,
        partner=rahul,
        status=OrderStatus.DELIVERED.value,
        address=address,
        notes="Extra chutney.",
        lines=[(momos, 1), (iced_tea, 1)],
        created_at=now - timedelta(days=1, hours=4),
        updated_at=now - timedelta(days=1, hours=3),
        events=[
            (OrderStatus.PLACED.value, "Order placed", now - timedelta(days=1, hours=4)),
            (OrderStatus.DELIVERED.value, "Delivered", now - timedelta(days=1, hours=3)),
        ],
    )

    _order(
        db,
        customer=aisha,
        restaurant=cafe,
        partner=None,
        status=OrderStatus.PREPARING.value,
        address=address,
        notes=None,
        lines=[(sandwich, 1), (filter_coffee, 1)],
        created_at=now - timedelta(minutes=25),
        updated_at=now - timedelta(minutes=10),
        events=[
            (OrderStatus.PLACED.value, "Order placed", now - timedelta(minutes=25)),
            (OrderStatus.ACCEPTED.value, "Kitchen accepted the order", now - timedelta(minutes=18)),
            (OrderStatus.PREPARING.value, "Cooking started", now - timedelta(minutes=10)),
        ],
    )

    _order(
        db,
        customer=aisha,
        restaurant=north,
        partner=None,
        status=OrderStatus.PLACED.value,
        address=address,
        notes=None,
        lines=[(biryani, 1)],
        created_at=now - timedelta(minutes=5),
        updated_at=now - timedelta(minutes=5),
        events=[(OrderStatus.PLACED.value, "Order placed", now - timedelta(minutes=5))],
    )

    assigned = _order(
        db,
        customer=aisha,
        restaurant=burger,
        partner=sana,
        status=OrderStatus.ASSIGNED.value,
        address=address,
        notes=None,
        lines=[(paneer_stack, 1), (cold_coffee, 1)],
        created_at=now - timedelta(minutes=40),
        updated_at=now - timedelta(minutes=8),
        events=[
            (OrderStatus.PLACED.value, "Order placed", now - timedelta(minutes=40)),
            (OrderStatus.ACCEPTED.value, "Kitchen accepted the order", now - timedelta(minutes=35)),
            (OrderStatus.PREPARING.value, "Cooking started", now - timedelta(minutes=28)),
            (OrderStatus.READY.value, "Packed and ready", now - timedelta(minutes=12)),
            (OrderStatus.ASSIGNED.value, "Assigned to Sana Iqbal", now - timedelta(minutes=8)),
        ],
    )

    _order(
        db,
        customer=aisha,
        restaurant=noodles,
        partner=rahul,
        status=OrderStatus.OUT_FOR_DELIVERY.value,
        address=address,
        notes="Call when you reach the gate.",
        lines=[(chicken_noodles, 1)],
        created_at=now - timedelta(minutes=50),
        updated_at=now - timedelta(minutes=6),
        events=[
            (OrderStatus.PLACED.value, "Order placed", now - timedelta(minutes=50)),
            (OrderStatus.READY.value, "Packed and ready", now - timedelta(minutes=20)),
            (OrderStatus.ASSIGNED.value, "Assigned to Rahul More", now - timedelta(minutes=15)),
            (OrderStatus.OUT_FOR_DELIVERY.value, "Out for delivery", now - timedelta(minutes=6)),
        ],
    )

    stale = _order(
        db,
        customer=aisha,
        restaurant=north,
        partner=None,
        status=OrderStatus.ACCEPTED.value,
        address=address,
        notes=None,
        lines=[(dal, 1), (jamun, 1)],
        created_at=now - timedelta(minutes=40),
        updated_at=now - timedelta(minutes=30),
        events=[
            (OrderStatus.PLACED.value, "Order placed", now - timedelta(minutes=40)),
            (OrderStatus.ACCEPTED.value, "Kitchen accepted the order", now - timedelta(minutes=30)),
        ],
    )
    db.add(
        ReminderLog(
            order_id=stale.id,
            restaurant_id=north.id,
            message="Order is still ACCEPTED and has not been updated for over 15 minutes.",
            is_read=False,
            created_at=now - timedelta(minutes=2),
        )
    )

    # Silence unused-name warnings in editors by referencing the leftover dishes.
    _ = (admin, paneer, hakka, chilli, cappuccino, muffin, fruit, brownie, assigned)
    db.commit()
