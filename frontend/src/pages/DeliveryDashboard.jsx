import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import EmptyState from "../components/EmptyState";
import Loading from "../components/Loading";
import OrderActions from "../components/OrderActions";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import { useSocket } from "../context/SocketContext";
import { money, when } from "../utils/format";

const FILTERS = ["", "ASSIGNED", "OUT_FOR_DELIVERY", "DELIVERED"];

export default function DeliveryDashboard() {
  const { lastEvent } = useSocket();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (lastEvent?.order_id) setTick((value) => value + 1);
  }, [lastEvent]);

  useEffect(() => {
    setLoading(true);
    const params = { page, page_size: 6 };
    if (status) params.status = status;
    api
      .get("/api/orders", { params })
      .then((response) => {
        setData(response.data);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [status, page, tick]);

  return (
    <div>
      <p className="eyebrow">Delivery</p>
      <h1>Assigned runs</h1>
      <p className="lede">You only see orders a kitchen assigned to you.</p>
      <div className="chip-row">
        {FILTERS.map((item) => (
          <button
            type="button"
            key={item || "all"}
            className={status === item ? "chip on" : "chip"}
            onClick={() => {
              setPage(1);
              setStatus(item);
            }}
          >
            {item === "" ? "All" : item === "OUT_FOR_DELIVERY" ? "On the way" : item === "DELIVERED" ? "History" : "Ready to pick up"}
          </button>
        ))}
      </div>
      {error ? <p className="error-text">{error}</p> : null}
      {loading ? <Loading /> : null}
      {!loading && data?.items?.length === 0 ? (
        <EmptyState title="Nothing assigned" text="When a kitchen marks an order ready and picks you, it lands here." />
      ) : null}
      <div className="stack">
        {data?.items?.map((order) => (
          <article className="card order-card" key={order.id}>
            <div className="order-top">
              <div>
                <p className="eyebrow">{order.restaurant_name}</p>
                <h2>
                  <Link to={`/orders/${order.id}`}>Order #{order.id}</Link>
                </h2>
                <p>
                  {order.customer_name} · {order.customer_phone || "No phone"}
                </p>
                <p className="muted">{order.delivery_address}</p>
                <p className="meta">{when(order.created_at)}</p>
              </div>
              <StatusBadge status={order.status} />
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
            {order.notes ? <p className="muted">Note: {order.notes}</p> : null}
            <div className="order-foot">
              <strong>{money(order.total_amount)}</strong>
              <OrderActions order={order} role="delivery" onChanged={() => setTick((value) => value + 1)} />
            </div>
          </article>
        ))}
      </div>
      <Pagination page={data?.page || 1} pages={data?.pages || 0} onChange={setPage} />
    </div>
  );
}
