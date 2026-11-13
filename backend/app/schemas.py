from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str
    role: str
    is_active: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(default="", max_length=20)
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AdminUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(default="", max_length=20)
    password: str = Field(min_length=8, max_length=72)
    role: Literal["customer", "owner", "delivery"]


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    is_active: bool | None = None
    role: Literal["customer", "owner", "delivery", "admin"] | None = None


class RestaurantIn(BaseModel):
    owner_id: int
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=1000)
    cuisine: str = Field(default="", max_length=80)
    address: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=20)
    emoji: str = Field(default="🍽️", max_length=8)
    is_active: bool = True


class RestaurantUpdate(BaseModel):
    owner_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    cuisine: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    emoji: str | None = Field(default=None, max_length=8)
    is_active: bool | None = None


class RestaurantOut(BaseModel):
    id: int
    owner_id: int
    owner_name: str | None = None
    name: str
    description: str
    cuisine: str
    address: str
    phone: str
    emoji: str
    is_active: bool
    rating: float | None = None
    review_count: int = 0


class MenuItemIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="Mains", max_length=80)
    price: float = Field(gt=0, le=10000)
    emoji: str = Field(default="🍽️", max_length=8)
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=80)
    price: float | None = Field(default=None, gt=0, le=10000)
    emoji: str | None = Field(default=None, max_length=8)
    is_available: bool | None = None


class MenuItemOut(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: str
    category: str
    price: float
    emoji: str
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class OrderItemIn(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=20)


class OrderCreate(BaseModel):
    restaurant_id: int
    delivery_address: str = Field(min_length=5, max_length=255)
    notes: str | None = Field(default=None, max_length=300)
    items: list[OrderItemIn] = Field(min_length=1)


class StatusUpdate(BaseModel):
    status: Literal[
        "ACCEPTED",
        "PREPARING",
        "READY",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "CANCELLED",
    ]


class AssignIn(BaseModel):
    delivery_partner_id: int


class OrderItemOut(BaseModel):
    id: int
    menu_item_id: int | None
    item_name: str
    quantity: int
    unit_price: float
    line_total: float


class StatusEventOut(BaseModel):
    id: int
    status: str
    note: str | None
    created_at: datetime


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class ReviewOut(BaseModel):
    id: int
    order_id: int
    customer_id: int
    restaurant_id: int
    customer_name: str | None = None
    rating: int
    comment: str | None
    created_at: datetime


class ReturnIn(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


class ReturnDecision(BaseModel):
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=300)


class ReturnOut(BaseModel):
    id: int
    order_id: int
    customer_id: int
    customer_name: str | None = None
    restaurant_name: str | None = None
    reason: str
    status: str
    owner_note: str | None
    created_at: datetime
    resolved_at: datetime | None


class OrderSummary(BaseModel):
    id: int
    status: str
    payment_status: str
    total_amount: float
    delivery_address: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    customer_id: int
    customer_name: str
    customer_phone: str
    restaurant_id: int
    restaurant_name: str
    restaurant_emoji: str
    delivery_partner_id: int | None
    delivery_partner_name: str | None
    items: list[OrderItemOut]
    review: ReviewOut | None
    return_request: ReturnOut | None


class PaymentOut(BaseModel):
    id: int
    entry_type: str
    amount: float
    status: str
    note: str | None
    created_at: datetime


class OrderDetail(OrderSummary):
    events: list[StatusEventOut]
    payments: list[PaymentOut]


class PageRestaurants(BaseModel):
    items: list[RestaurantOut]
    total: int
    page: int
    page_size: int
    pages: int


class PageMenu(BaseModel):
    items: list[MenuItemOut]
    total: int
    page: int
    page_size: int
    pages: int


class PageOrders(BaseModel):
    items: list[OrderSummary]
    total: int
    page: int
    page_size: int
    pages: int


class PageUsers(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int
    pages: int


class PageReviews(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    page_size: int
    pages: int


class PageReturns(BaseModel):
    items: list[ReturnOut]
    total: int
    page: int
    page_size: int
    pages: int


class DishStat(BaseModel):
    name: str
    quantity: int


class StatsOut(BaseModel):
    restaurant_count: int
    total_orders: int
    active_orders: int
    orders_today: int
    revenue: float
    average_rating: float | None
    review_count: int
    unread_reminders: int
    top_dishes: list[DishStat]
    orders_by_status: dict[str, int]


class SnapshotOrder(BaseModel):
    id: int
    restaurant: str
    status: str
    total_amount: float
    created_at: datetime


class SnapshotOut(BaseModel):
    order_count: int
    open_count: int
    spend_this_week: float
    top_items: list[DishStat]
    last_five: list[SnapshotOrder]
    open_orders: list[SnapshotOrder]


class ReminderOut(BaseModel):
    id: int
    order_id: int
    restaurant_id: int
    restaurant_name: str
    message: str
    is_read: bool
    created_at: datetime


class PageReminders(BaseModel):
    items: list[ReminderOut]
    total: int
    page: int
    page_size: int
    pages: int


class InsightIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class InsightOut(BaseModel):
    answer: str
    source: Literal["openai", "local"]


class PartnerOut(BaseModel):
    id: int
    full_name: str
    phone: str
