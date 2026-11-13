from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import MenuItem, Restaurant, User, UserRole
from app.schemas import MenuItemIn, MenuItemOut, MenuItemUpdate, PageMenu
from app.serializers import page_dict

router = APIRouter(prefix="/api/menu", tags=["menu"])


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _owned_restaurant(db: Session, user: User, restaurant_id: int) -> Restaurant:
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None or restaurant.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


def _owned_item(db: Session, user: User, item_id: int) -> MenuItem:
    item = db.get(MenuItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dish not found")
    _owned_restaurant(db, user, item.restaurant_id)
    return item


@router.get("", response_model=PageMenu)
def my_menu(
    restaurant_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    """Owner menu, including dishes marked unavailable."""
    ids = [row[0] for row in db.query(Restaurant.id).filter(Restaurant.owner_id == user.id).all()]
    if restaurant_id is not None and restaurant_id not in ids:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    target_ids = [restaurant_id] if restaurant_id is not None else ids
    query = db.query(MenuItem).filter(MenuItem.restaurant_id.in_(target_ids or [-1]))
    total = query.count()
    rows = query.order_by(MenuItem.restaurant_id, MenuItem.category, MenuItem.name).offset((page - 1) * page_size).limit(page_size).all()
    return page_dict([MenuItemOut.model_validate(row) for row in rows], total, page, page_size)


@router.post("/restaurants/{restaurant_id}", response_model=MenuItemOut, status_code=201)
def create_item(
    restaurant_id: int,
    body: MenuItemIn,
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    _owned_restaurant(db, user, restaurant_id)
    item = MenuItem(
        restaurant_id=restaurant_id,
        name=body.name.strip(),
        description=body.description.strip(),
        category=body.category.strip() or "Mains",
        price=_money(body.price),
        emoji=body.emoji.strip() or "🍽️",
        is_available=body.is_available,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=MenuItemOut)
def update_item(
    item_id: int,
    body: MenuItemUpdate,
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    item = _owned_item(db, user, item_id)
    data = body.model_dump(exclude_unset=True)
    if "price" in data and data["price"] is not None:
        data["price"] = _money(data["price"])
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}/availability", response_model=MenuItemOut)
def set_availability(
    item_id: int,
    body: MenuItemUpdate,
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    if body.is_available is None:
        raise HTTPException(status_code=400, detail="is_available is required")
    item = _owned_item(db, user, item_id)
    item.is_available = body.is_available
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    user: User = Depends(require_roles(UserRole.owner.value)),
    db: Session = Depends(get_db),
):
    item = _owned_item(db, user, item_id)
    db.delete(item)
    db.commit()
