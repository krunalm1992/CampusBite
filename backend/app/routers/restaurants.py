from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_optional_user
from app.models import MenuItem, Restaurant, Review, User
from app.schemas import MenuItemOut, PageMenu, PageRestaurants, PageReviews, RestaurantOut, ReviewOut
from app.serializers import page_dict, restaurant_out, restaurant_ratings, review_out

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])


def _visible_restaurant(restaurant: Restaurant | None, user: User | None) -> Restaurant:
    from fastapi import HTTPException

    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if restaurant.is_active:
        return restaurant
    if user and (user.role == "admin" or user.id == restaurant.owner_id):
        return restaurant
    raise HTTPException(status_code=404, detail="Restaurant not found")


@router.get("/cuisines", response_model=list[str])
def cuisines(db: Session = Depends(get_db)):
    rows = (
        db.query(Restaurant.cuisine)
        .filter(Restaurant.is_active.is_(True), Restaurant.cuisine != "")
        .distinct()
        .order_by(Restaurant.cuisine)
        .all()
    )
    return [row[0] for row in rows]


@router.get("", response_model=PageRestaurants)
def list_restaurants(
    q: str | None = None,
    cuisine: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(9, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(Restaurant).filter(Restaurant.is_active.is_(True))
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(Restaurant.name.ilike(like), Restaurant.cuisine.ilike(like), Restaurant.description.ilike(like))
        )
    if cuisine and cuisine.strip():
        query = query.filter(Restaurant.cuisine.ilike(cuisine.strip()))
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


@router.get("/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    restaurant = (
        db.query(Restaurant)
        .options(joinedload(Restaurant.owner))
        .filter(Restaurant.id == restaurant_id)
        .first()
    )
    restaurant = _visible_restaurant(restaurant, user)
    rating, count = restaurant_ratings(db, [restaurant.id])[restaurant.id]
    return restaurant_out(restaurant, rating, count)


@router.get("/{restaurant_id}/menu", response_model=PageMenu)
def restaurant_menu(
    restaurant_id: int,
    q: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    restaurant = db.get(Restaurant, restaurant_id)
    _visible_restaurant(restaurant, user)
    if min_price is not None and max_price is not None and min_price > max_price:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Minimum price cannot be higher than maximum price")
    query = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id, MenuItem.is_available.is_(True))
    if q and q.strip():
        query = query.filter(MenuItem.name.ilike(f"%{q.strip()}%"))
    if category and category.strip():
        query = query.filter(MenuItem.category.ilike(category.strip()))
    if min_price is not None:
        query = query.filter(MenuItem.price >= min_price)
    if max_price is not None:
        query = query.filter(MenuItem.price <= max_price)
    total = query.count()
    rows = query.order_by(MenuItem.category, MenuItem.name).offset((page - 1) * page_size).limit(page_size).all()
    return page_dict([MenuItemOut.model_validate(row) for row in rows], total, page, page_size)


@router.get("/{restaurant_id}/reviews", response_model=PageReviews)
def restaurant_reviews(
    restaurant_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id, Restaurant.is_active.is_(True)).first()
    if restaurant is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Restaurant not found")
    query = db.query(Review, User.full_name).join(User, User.id == Review.customer_id).filter(Review.restaurant_id == restaurant_id)
    total = query.count()
    rows = query.order_by(Review.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for review, name in rows:
        payload = review_out(review, name)
        items.append(payload)
    return page_dict(items, total, page, page_size)
