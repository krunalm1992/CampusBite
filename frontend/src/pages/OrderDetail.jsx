import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import Loading from "../components/Loading";
import OrderActions from "../components/OrderActions";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";
import { useSocket } from "../context/SocketContext";
import { label, money, when } from "../utils/format";

export default function OrderDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const { lastEvent, connected } = useSocket();
  const [order, setOrder] = useState(null);
  const [partners, setPartners] = useState([]);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (String(lastEvent?.order_id) === String(id)) setTick((value) => value + 1);
  }, [lastEvent, id]);

  useEffect(() => {
    api
      .get(`/api/orders/${id}`)
      .then((response) => {
        setOrder(response.data);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)));
  }, [id, tick]);

  useEffect(() => {
    if (user?.role === "owner") {
      api.get("/api/owner/partners").then((response) => setPartners(response.data)).catch(() => {});
    }
  }, [user]);

  if (error) return <p className="error-text">{error}</p>;
  if (!order) return <Loading label="Loading order" />;

  const back = user?.role === "owner" ? "/owner/orders" : user?.role === "delivery" ? "/delivery" : "/orders";

  return (
    <div>
      <Link to={back} className="back-link">
        Back to orders
      </Link>
      <div className="dashboard-head">
        <div>
          <p className="eyebrow">
            {order.restaurant_emoji} {order.restaurant_name}
            {connected ? " · live" : ""}
          </p>
          <h1>Order #{order.id}</h1>
          <p className="meta">Placed {when(order.created_at)}</p>
        </div>
        <div className="badge-row">
          <StatusBadge status={order.status} />
          <StatusBadge status={order.payment_status} />
        </div>
      </div>

      <div className="split">
        <section className="card">
          <h2>Timeline</h2>
          <ol className="timeline">
            {order.events.map((event) => (
              <li key={event.id}>
                <strong>{label(event.status)}</strong>
                <span>{event.note}</span>
                <time>{when(event.created_at)}</time>
              </li>
            ))}
          </ol>
        </section>
        <section className="stack">
          <article className="card">
            <h2>Delivery</h2>
            <p>{order.delivery_address}</p>
            <p className="meta">
              {order.customer_name} · {order.customer_phone || "No phone"}
            </p>
            {order.delivery_partner_name ? <p className="meta">Partner: {order.delivery_partner_name}</p> : null}
            {order.notes ? <p className="muted">Note: {order.notes}</p> : null}
          </article>
          <article className="card">
            <h2>Items</h2>
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
            <p className="price-lg">{money(order.total_amount)}</p>
            <OrderActions order={order} role={user?.role} partners={partners} onChanged={() => setTick((value) => value + 1)} />
          </article>
          <article className="card">
            <h2>Payment ledger</h2>
            {order.payments?.length ? (
              <ul className="plain-list">
                {order.payments.map((payment) => (
                  <li key={payment.id}>
                    <span>
                      {payment.entry_type} · {payment.note || payment.status}
                    </span>
                    <span>{money(payment.amount)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No ledger rows.</p>
            )}
          </article>
        </section>
      </div>
    </div>
  );
}
