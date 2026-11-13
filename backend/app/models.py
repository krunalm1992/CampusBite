"""Relational models for CampusBite.

Money is stored as Numeric so totals stay exact. Order items snapshot the
name and price so later menu edits do not rewrite history.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    customer = "customer"
    owner = "owner"
    delivery = "delivery"
    admin = "admin"


class OrderStatus(str, enum.Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    ASSIGNED = "ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, enum.Enum):
    mock_paid = "mock_paid"
    refunded = "refunded"


class ReturnStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    restaurants: Mapped[list["Restaurant"]] = relationship(back_populates="owner")
    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer", foreign_keys="Order.customer_id"
    )
    deliveries: Mapped[list["Order"]] = relationship(
        back_populates="delivery_partner", foreign_keys="Order.delivery_partner_id"
    )


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    cuisine: Mapped[str] = mapped_column(String(80), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    emoji: Mapped[str] = mapped_column(String(8), default="🍽️")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="restaurants")
    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurant")
    orders: Mapped[list["Order"]] = relationship(back_populates="restaurant")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="Mains")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    emoji: Mapped[str] = mapped_column(String(8), default="🍽️")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="menu_items")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    delivery_partner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.PLACED.value, index=True)
    payment_status: Mapped[str] = mapped_column(String(32), default=PaymentStatus.mock_paid.value)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    delivery_address: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer: Mapped[User] = relationship(back_populates="orders", foreign_keys=[customer_id])
    restaurant: Mapped[Restaurant] = relationship(back_populates="orders")
    delivery_partner: Mapped[User | None] = relationship(
        back_populates="deliveries", foreign_keys=[delivery_partner_id]
    )
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    events: Mapped[list["OrderStatusEvent"]] = relationship(back_populates="order")
    review: Mapped["Review | None"] = relationship(back_populates="order", uselist=False)
    payments: Mapped[list["PaymentLedger"]] = relationship(back_populates="order")
    return_request: Mapped["ReturnRequest | None"] = relationship(back_populates="order", uselist=False)
    reminders: Mapped[list["ReminderLog"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    # Kept if the dish is later deleted, so the receipt still makes sense.
    menu_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True
    )
    item_name: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="events")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # One review per delivered order.
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="review")


class PaymentLedger(Base):
    """Dummy payment trail. No real gateway is involved."""

    __tablename__ = "payment_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(20))  # charge | refund
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="payments")


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # A customer cannot open a second return for the same order.
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=ReturnStatus.pending.value, index=True)
    owner_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="return_request")


class ReminderLog(Base):
    """Owner-facing reminder for an order that has sat too long without an update."""

    __tablename__ = "reminder_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    message: Mapped[str] = mapped_column(String(255))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="reminders")
