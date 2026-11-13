import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import EmptyState from "../components/EmptyState";
import Loading from "../components/Loading";
import OrderActions from "../components/OrderActions";
import OrderFilters from "../components/OrderFilters";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import { useSocket } from "../context/SocketContext";
import { money, when } from "../utils/format";

export default function OwnerOrders() {
  const { lastEvent } = useSocket();
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [restaurantId, setRestaurantId] = useState("");
  const [restaurants, setRestaurants] = useState([]);
  const [partners, setPartners] = useState([]);
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [returnsPage, setReturnsPage] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (lastEvent) setTick((value) => value + 1);
  }, [lastEvent]);

  useEffect(() => {
    api.get("/api/owner/restaurants").then((response) => setRestaurants(response.data)).catch(() => {});
    api.get("/api/owner/partners").then((response) => setPartners(response.data)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = { page, page_size: 6 };
    if (status) params.status = status;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (restaurantId) params.restaurant_id = restaurantId;
    Promise.all([
      api.get("/api/orders", { params }),
      api.get("/api/returns", { params: { status: "pending", page_size: 10 } }),
    ])
      .then(([orders, returns]) => {
        setData(orders.data);
        setReturnsPage(returns.data);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [status, dateFrom, dateTo, restaurantId, page, tick]);

  return (
    <div>
      <div className="dashboard-head">
        <div>
          <p className="eyebrow">Kitchen</p>
          <h1>Incoming orders</h1>
        </div>
      </div>
      <OrderFilters
        status={status}
        setStatus={(value) => {
          setPage(1);
          setStatus(value);
        }}
        dateFrom={dateFrom}
        setDateFrom={(value) => {
          setPage(1);
          setDateFrom(value);
        }}
        dateTo={dateTo}
        setDateTo={(value) => {
          setPage(1);
          setDateTo(value);
        }}
      />
      {restaurants.length > 1 ? (
        <label className="filters">
          Restaurant
          <select
            value={restaurantId}
            onChange={(event) => {
              setPage(1);
              setRestaurantId(event.target.value);
            }}
          >
            <option value="">All of yours</option>
            {restaurants.map((restaurant) => (
              <option key={restaurant.id} value={restaurant.id}>
                {restaurant.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {returnsPage?.items?.length ? (
        <section className="section">
          <h2>Return requests</h2>
          <div className="stack">
            {returnsPage.items.map((item) => (
              <article className="card" key={item.id}>
                <p className="eyebrow">{item.restaurant_name}</p>
                <h3>
                  Order #{item.order_id} · {item.customer_name}
                </h3>
                <p>{item.reason}</p>
                <Link to={`/orders/${item.order_id}`}>Open order to approve or reject</Link>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {error ? <p className="error-text">{error}</p> : null}
      {loading ? <Loading /> : null}
      {!loading && data?.items?.length === 0 ? <EmptyState title="No orders in this filter" /> : null}
      <div className="stack">
        {data?.items?.map((order) => (
          <article className="card order-card" key={order.id}>
            <div className="order-top">
              <div>
                <p className="eyebrow">{order.restaurant_name}</p>
                <h2>
                  <Link to={`/orders/${order.id}`}>Order #{order.id}</Link>
                </h2>
                <p className="meta">
                  {order.customer_name} · {order.customer_phone || "No phone"} · {when(order.created_at)}
                </p>
                <p className="muted">{order.delivery_address}</p>
              </div>
              <div className="badge-row">
                <StatusBadge status={order.status} />
                <StatusBadge status={order.payment_status} />
                {order.return_request ? <StatusBadge status={order.return_request.status} /> : null}
              </div>
            </div>
            <ul className="plain-list">
              {order.items.map((item) => (
                <li key={item.id}>
                  <span>
                    {item.quantity} × {item.item_name}
                  </span>
                  <span>{money(item.line_total)}</span>
                </li>
              ))}
            </ul>
            {order.return_request?.status === "pending" ? <p className="muted">Return reason: {order.return_request.reason}</p> : null}
            <div className="order-foot">
              <strong>{money(order.total_amount)}</strong>
              <OrderActions order={order} role="owner" partners={partners} onChanged={() => setTick((value) => value + 1)} />
            </div>
          </article>
        ))}
      </div>
      <Pagination page={data?.page || 1} pages={data?.pages || 0} onChange={setPage} />
    </div>
  );
}
