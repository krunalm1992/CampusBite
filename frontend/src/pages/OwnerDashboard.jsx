import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import Loading from "../components/Loading";
import { useSocket } from "../context/SocketContext";
import { useToast } from "../context/ToastContext";
import { label, money, when } from "../utils/format";

export default function OwnerDashboard() {
  const { lastEvent } = useSocket();
  const { push } = useToast();
  const [stats, setStats] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [restaurants, setRestaurants] = useState([]);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (lastEvent) setTick((value) => value + 1);
  }, [lastEvent]);

  useEffect(() => {
    Promise.all([
      api.get("/api/owner/stats"),
      api.get("/api/owner/reminders", { params: { unread_only: true, page_size: 8 } }),
      api.get("/api/owner/restaurants"),
    ])
      .then(([statsRes, reminderRes, restaurantRes]) => {
        setStats(statsRes.data);
        setReminders(reminderRes.data.items);
        setRestaurants(restaurantRes.data);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)));
  }, [tick]);

  async function markRead(id) {
    try {
      await api.post(`/api/owner/reminders/${id}/read`);
      setTick((value) => value + 1);
    } catch (err) {
      push(errorMessage(err));
    }
  }

  if (error) return <p className="error-text">{error}</p>;
  if (!stats) return <Loading />;

  return (
    <div>
      <div className="dashboard-head">
        <div>
          <p className="eyebrow">Kitchen</p>
          <h1>Restaurant dashboard</h1>
        </div>
        <div className="user-chip">
          <Link className="btn btn-primary btn-small" to="/owner/orders">
            Manage orders
          </Link>
          <Link className="btn btn-ghost btn-small" to="/owner/menu">
            Edit menu
          </Link>
        </div>
      </div>

      <div className="stats">
        <article className="stat"><span>Orders</span><strong>{stats.total_orders}</strong></article>
        <article className="stat"><span>Active</span><strong>{stats.active_orders}</strong></article>
        <article className="stat"><span>Today</span><strong>{stats.orders_today}</strong></article>
        <article className="stat"><span>Revenue</span><strong>{money(stats.revenue)}</strong></article>
        <article className="stat"><span>Rating</span><strong>{stats.average_rating ?? "—"}</strong></article>
      </div>

      <section className="section">
        <div className="dashboard-head">
          <h2>Stale-order reminders</h2>
          {reminders.length ? (
            <button
              type="button"
              className="btn btn-ghost btn-small"
              onClick={async () => {
                await api.post("/api/owner/reminders/read-all");
                setTick((value) => value + 1);
              }}
            >
              Mark all read
            </button>
          ) : null}
        </div>
        {reminders.length === 0 ? <p className="muted">No unread reminders. Orders left in Placed or Accepted for 15 minutes show up here.</p> : null}
        <div className="stack">
          {reminders.map((reminder) => (
            <article className="card reminder" key={reminder.id}>
              <div>
                <strong>{reminder.restaurant_name}</strong>
                <p>{reminder.message}</p>
                <p className="meta">{when(reminder.created_at)}</p>
              </div>
              <button type="button" className="btn btn-small btn-ghost" onClick={() => markRead(reminder.id)}>
                Dismiss
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="section">
        <h2>Your counters</h2>
        <div className="grid-cards">
          {restaurants.map((restaurant) => (
            <article className="card" key={restaurant.id}>
              <p className="eyebrow">{restaurant.emoji} {restaurant.cuisine}</p>
              <h3>{restaurant.name}</h3>
              <p className="muted">{restaurant.address}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section">
        <h2>Popular dishes</h2>
        {stats.top_dishes.length === 0 ? <p className="muted">No dishes sold yet.</p> : (
          <ul className="plain-list card">
            {stats.top_dishes.map((dish) => (
              <li key={dish.name}>
                <span>{dish.name}</span>
                <span>{dish.quantity} ordered</span>
              </li>
            ))}
          </ul>
        )}
        {Object.keys(stats.orders_by_status).length ? (
          <p className="meta status-line">
            {Object.entries(stats.orders_by_status).map(([status, count]) => `${label(status)} ${count}`).join(" · ")}
          </p>
        ) : null}
      </section>
    </div>
  );
}
