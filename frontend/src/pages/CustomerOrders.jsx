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

export default function CustomerOrders() {
  const { lastEvent } = useSocket();
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (lastEvent?.order_id || lastEvent?.type === "return.updated") setTick((value) => value + 1);
  }, [lastEvent]);

  useEffect(() => {
    setLoading(true);
    const params = { page, page_size: 6 };
    if (status) params.status = status;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    api
      .get("/api/orders", { params })
      .then((response) => {
        setData(response.data);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [status, dateFrom, dateTo, page, tick]);

  return (
    <div>
      <div className="dashboard-head">
        <div>
          <p className="eyebrow">Student</p>
          <h1>Your orders</h1>
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
      {error ? <p className="error-text">{error}</p> : null}
      {loading ? <Loading /> : null}
      {!loading && data?.items?.length === 0 ? <EmptyState title="No orders in this filter" text="Place an order or clear the filters." /> : null}
      <div className="stack">
        {data?.items?.map((order) => (
          <article className="card order-card" key={order.id}>
            <div className="order-top">
              <div>
                <p className="eyebrow">
                  {order.restaurant_emoji} {order.restaurant_name}
                </p>
                <h2>
                  <Link to={`/orders/${order.id}`}>Order #{order.id}</Link>
                </h2>
                <p className="meta">{when(order.created_at)}</p>
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
            <div className="order-foot">
              <strong>{money(order.total_amount)}</strong>
              <OrderActions order={order} role="customer" onChanged={() => setTick((value) => value + 1)} />
            </div>
          </article>
        ))}
      </div>
      <Pagination page={data?.page || 1} pages={data?.pages || 0} onChange={setPage} />
    </div>
  );
}
