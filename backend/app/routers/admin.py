from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_roles
from app.models import Restaurant, User, UserRole
from app.schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    PageRestaurants,
    PageUsers,
    RestaurantIn,
    RestaurantOut,
    RestaurantUpdate,
    UserOut,
)
from app.security import hash_password
from app.serializers import page_dict, restaurant_out, restaurant_ratings

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_owner(db: Session, owner_id: int) -> User:
    owner = db.get(User, owner_id)
    if owner is None or owner.role != UserRole.owner.value or not owner.is_active:
        raise HTTPException(status_code=400, detail="Choose an active restaurant owner")
    return owner


@router.get("/users", response_model=PageUsers)
def list_users(
    q: str | None = None,
    role: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    _: User = Depends(require_roles(UserRole.admin.value)),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(User.full_name.ilike(like), User.email.ilike(like)))
    total = query.count()
    rows = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return page_dict([UserOut.model_validate(row) for row in rows], total, page, page_size)


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    body: AdminUserCreate,
    _: User = Depends(require_roles(UserRole.admin.value)),
    db: Session = Depends(get_db),
):
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    try:
        password_hash = hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    user = User(
        full_name=body.full_name.strip(),
        email=email,
        phone=body.phone.strip(),
        password_hash=password_hash,
        role=body.role,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: AdminUserUpdate,
    actor: User = Depends(require_roles(UserRole.admin.value)),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == actor.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    if user.id == actor.id and body.role and body.role != actor.role:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.phone is not None:
        user.phone = body.phone.strip()
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role
    if body.password:
        try:
            user.password_hash = hash_password(body.password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)
    return user


@router.get("/restaurants", response_model=PageRestaurants)
def list_restaurants(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    _: User = Depends(require_roles(UserRole.admin.value)),
    db: Session = Depends(get_db),
):
    query = db.query(Restaurant)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(Restaurant.name.ilike(like), Restaurant.cuisine.ilike(like)))
    total = query.count()
    rows = (
        query.options(joinedload(Restaurant.owner))
        .order_by(Restaurant.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    ratings = restaurant_ratings(db, [row.id for row in rows])
    items = [restaurant_out(row, *ratings[row.id]) for row in rows]
    return page_dict(items, total, page, page_size)


@router.post("/restaurants", response_model=RestaurantOut, status_code=201)
def create_restaurant(
    body: RestaurantIn,
    _: User = Depends(require_roles(UserRole.admin.value)),
    db: Session = Depends(get_db),
):
    owner = _require_owner(db, body.owner_id)
    restaurant = Restaurant(
        owner_id=owner.id,
        name=body.name.strip(),
        description=body.description.strip(),
        cuisine=body.cuisine.strip(),
        address=body.address.strip(),
        phone=body.phone.strip(),
        emoji=body.emoji.strip() or "🍽️",
        is_active=body.is_active,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    restaurant.owner = owner
    rating, count = restaurant_ratings(db, [restaurant.id])[restaurant.id]
    return restaurant_out(restaurant, rating, count)


@router.patch("/restaurants/{restaurant_id}", response_model=RestaurantOut)
def update_restaurant(
    restaurant_id: int,
    body: RestaurantUpdate,
    _: User = Depends(require_roles(UserRole.admin.value)),
    db: Session = Depends(get_db),
):
    restaurant = db.query(Restaurant).options(joinedload(Restaurant.owner)).filter(Restaurant.id == restaurant_id).first()
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    data = body.model_dump(exclude_unset=True)
    if "owner_id" in data and data["owner_id"] is not None:
        _require_owner(db, data["owner_id"])
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(restaurant, key, value)
    db.commit()
    db.refresh(restaurant)
    rating, count = restaurant_ratings(db, [restaurant.id])[restaurant.id]
    return restaurant_out(restaurant, rating, count)
