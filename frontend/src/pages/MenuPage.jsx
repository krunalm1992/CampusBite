import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import EmptyState from "../components/EmptyState";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";
import StarRating from "../components/StarRating";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useToast } from "../context/ToastContext";
import { money, when } from "../utils/format";

export default function MenuPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { items, addItem, setQuantity } = useCart();
  const { push } = useToast();
  const navigate = useNavigate();
  const [restaurant, setRestaurant] = useState(null);
  const [q, setQ] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [page, setPage] = useState(1);
  const [menu, setMenu] = useState(null);
  const [reviews, setReviews] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get(`/api/restaurants/${id}`)
      .then((response) => setRestaurant(response.data))
      .catch((err) => setError(errorMessage(err)));
    api
      .get(`/api/restaurants/${id}/reviews`, { params: { page_size: 5 } })
      .then((response) => setReviews(response.data))
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    const handle = setTimeout(() => {
      setLoading(true);
      const params = { page, page_size: 12 };
      if (q.trim()) params.q = q.trim();
      if (minPrice !== "") params.min_price = minPrice;
      if (maxPrice !== "") params.max_price = maxPrice;
      api
        .get(`/api/restaurants/${id}/menu`, { params })
        .then((response) => {
          setMenu(response.data);
          setError("");
        })
        .catch((err) => setError(errorMessage(err)))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [id, q, minPrice, maxPrice, page]);

  function onAdd(dish) {
    if (!restaurant) return;
    if (!user) {
      navigate("/login");
      return;
    }
    if (user.role !== "customer") {
      push("Only student accounts can place orders");
      return;
    }
    const added = addItem({
      menuItemId: dish.id,
      restaurantId: restaurant.id,
      restaurantName: restaurant.name,
      name: dish.name,
      price: dish.price,
      emoji: dish.emoji,
    });
    if (added) push(`${dish.name} added to cart`);
  }

  return (
    <div>
      <Link to="/" className="back-link">
        All restaurants
      </Link>
      {restaurant ? (
        <header className="restaurant-head">
          <div className="card-emoji lg">{restaurant.emoji}</div>
          <div>
            <p className="eyebrow">{restaurant.cuisine}</p>
            <h1>{restaurant.name}</h1>
            <p className="lede">{restaurant.description}</p>
            <p className="meta">
              {restaurant.address}
              {restaurant.rating ? ` · ${restaurant.rating} from ${restaurant.review_count} review${restaurant.review_count === 1 ? "" : "s"}` : ""}
            </p>
          </div>
        </header>
      ) : null}

      <div className="filters">
        <label>
          Dish name
          <input
            value={q}
            onChange={(event) => {
              setPage(1);
              setQ(event.target.value);
            }}
            placeholder="Search the menu"
          />
        </label>
        <label>
          Min price
          <input
            type="number"
            min="0"
            value={minPrice}
            onChange={(event) => {
              setPage(1);
              setMinPrice(event.target.value);
            }}
            placeholder="0"
          />
        </label>
        <label>
          Max price
          <input
            type="number"
            min="0"
            value={maxPrice}
            onChange={(event) => {
              setPage(1);
              setMaxPrice(event.target.value);
            }}
            placeholder="500"
          />
        </label>
      </div>

      {error ? <p className="error-text">{error}</p> : null}
      {loading ? <Loading label="Reading the menu" /> : null}
      {!loading && menu?.items?.length === 0 ? <EmptyState title="No dishes in this range" text="Widen the price filter or clear the search." /> : null}

      <div className="menu-list">
        {menu?.items?.map((dish) => {
          const inCart = items.find((row) => row.menuItemId === dish.id);
          return (
            <article className="card menu-row" key={dish.id}>
              <div className="card-emoji">{dish.emoji}</div>
              <div>
                <p className="eyebrow">{dish.category}</p>
                <h2>{dish.name}</h2>
                <p className="muted">{dish.description}</p>
              </div>
              <div className="menu-buy">
                <strong>{money(dish.price)}</strong>
                {inCart ? (
                  <div className="qty">
                    <button type="button" onClick={() => setQuantity(dish.id, inCart.quantity - 1)} aria-label="Decrease">
                      −
                    </button>
                    <span>{inCart.quantity}</span>
                    <button type="button" onClick={() => setQuantity(dish.id, Math.min(20, inCart.quantity + 1))} aria-label="Increase">
                      +
                    </button>
                  </div>
                ) : (
                  <button type="button" className="btn btn-primary btn-small" onClick={() => onAdd(dish)}>
                    Add
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
      <Pagination page={menu?.page || 1} pages={menu?.pages || 0} onChange={setPage} />

      {reviews?.items?.length ? (
        <section className="section">
          <h2>Recent reviews</h2>
          <div className="stack">
            {reviews.items.map((review) => (
              <article className="card review" key={review.id}>
                <StarRating value={review.rating} />
                <p>{review.comment || "No written comment."}</p>
                <p className="meta">
                  {review.customer_name} · {when(review.created_at)}
                </p>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
