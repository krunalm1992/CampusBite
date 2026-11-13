import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import EmptyState from "../components/EmptyState";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";
import StarRating from "../components/StarRating";

export default function Home() {
  const [q, setQ] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [cuisines, setCuisines] = useState([]);
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/restaurants/cuisines").then((response) => setCuisines(response.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const handle = setTimeout(() => {
      setLoading(true);
      const params = { page, page_size: 9 };
      if (q.trim()) params.q = q.trim();
      if (cuisine) params.cuisine = cuisine;
      api
        .get("/api/restaurants", { params })
        .then((response) => {
          setData(response.data);
          setError("");
        })
        .catch((err) => setError(errorMessage(err)))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [q, cuisine, page]);

  return (
    <div>
      <section className="hero">
        <p className="eyebrow">Campus canteen, delivered</p>
        <h1>Hot food between classes.</h1>
        <p className="lede">
          Browse the counters that actually cook for this campus, build a cart, and follow the order from the kitchen to your hostel gate.
        </p>
        <label className="search">
          <span className="sr">Search restaurants</span>
          <input
            value={q}
            onChange={(event) => {
              setPage(1);
              setQ(event.target.value);
            }}
            placeholder="Search mess, cafe, noodles..."
          />
        </label>
        <div className="chip-row">
          <button type="button" className={!cuisine ? "chip on" : "chip"} onClick={() => { setCuisine(""); setPage(1); }}>
            All
          </button>
          {cuisines.map((item) => (
            <button
              type="button"
              key={item}
              className={cuisine === item ? "chip on" : "chip"}
              onClick={() => {
                setCuisine(item);
                setPage(1);
              }}
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      {error ? <p className="error-text">{error}</p> : null}
      {loading ? <Loading label="Finding kitchens" /> : null}
      {!loading && data?.items?.length === 0 ? (
        <EmptyState title="No restaurants match" text="Try another cuisine or clear the search." />
      ) : null}
      <div className="grid-cards">
        {data?.items?.map((restaurant) => (
          <Link className="card restaurant-card" key={restaurant.id} to={`/restaurants/${restaurant.id}`}>
            <div className="card-emoji" aria-hidden="true">
              {restaurant.emoji}
            </div>
            <div>
              <p className="eyebrow">{restaurant.cuisine}</p>
              <h2>{restaurant.name}</h2>
              <p className="muted">{restaurant.description}</p>
              <p className="meta">{restaurant.address}</p>
              <div className="meta-row">
                {restaurant.review_count ? (
                  <span className="rating-inline">
                    <StarRating value={Math.round(restaurant.rating)} />
                    <span>{restaurant.rating}</span>
                  </span>
                ) : (
                  <span className="muted">New on campus</span>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>
      <Pagination page={data?.page || 1} pages={data?.pages || 0} onChange={setPage} />
    </div>
  );
}
