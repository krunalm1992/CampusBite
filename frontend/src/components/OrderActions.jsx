import { useState } from "react";
import api, { errorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import Modal from "./Modal";
import StarRating from "./StarRating";

const OWNER_STEP = {
  PLACED: { status: "ACCEPTED", label: "Accept order" },
  ACCEPTED: { status: "PREPARING", label: "Start preparing" },
  PREPARING: { status: "READY", label: "Mark ready" },
};

const DELIVERY_STEP = {
  ASSIGNED: { status: "OUT_FOR_DELIVERY", label: "Out for delivery" },
  OUT_FOR_DELIVERY: { status: "DELIVERED", label: "Mark delivered" },
};

export default function OrderActions({ order, role, partners = [], onChanged }) {
  const { push } = useToast();
  const [busy, setBusy] = useState(false);
  const [partnerId, setPartnerId] = useState(partners[0]?.id ? String(partners[0].id) : "");
  const [reviewOpen, setReviewOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");

  async function run(action) {
    setBusy(true);
    try {
      await action();
      onChanged?.();
    } catch (error) {
      push(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function advance(status) {
    if (status === "CANCELLED" && !window.confirm("Cancel this order?")) return;
    await run(() => api.post(`/api/orders/${order.id}/status`, { status }));
  }

  const step = role === "owner" ? OWNER_STEP[order.status] : role === "delivery" ? DELIVERY_STEP[order.status] : null;
  const canReview = role === "customer" && ["DELIVERED", "REFUNDED"].includes(order.status) && !order.review;
  const canReturn = role === "customer" && order.status === "DELIVERED" && !order.return_request;
  const pendingReturn = role === "owner" && order.return_request?.status === "pending";

  return (
    <div className="actions">
      {role === "customer" && order.status === "PLACED" ? (
        <button type="button" className="btn btn-danger btn-small" disabled={busy} onClick={() => advance("CANCELLED")}>
          Cancel order
        </button>
      ) : null}
      {step ? (
        <button type="button" className="btn btn-primary btn-small" disabled={busy} onClick={() => advance(step.status)}>
          {step.label}
        </button>
      ) : null}
      {role === "owner" && order.status === "READY" ? (
        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            run(() => api.post(`/api/orders/${order.id}/assign`, { delivery_partner_id: Number(partnerId) }));
          }}
        >
          <select value={partnerId} onChange={(event) => setPartnerId(event.target.value)} required>
            <option value="" disabled>
              Delivery partner
            </option>
            {partners.map((partner) => (
              <option key={partner.id} value={partner.id}>
                {partner.full_name}
              </option>
            ))}
          </select>
          <button type="submit" className="btn btn-primary btn-small" disabled={busy || !partnerId}>
            Assign
          </button>
        </form>
      ) : null}
      {canReview ? (
        <button type="button" className="btn btn-ghost btn-small" onClick={() => setReviewOpen(true)}>
          Rate order
        </button>
      ) : null}
      {canReturn ? (
        <button type="button" className="btn btn-ghost btn-small" onClick={() => setReturnOpen(true)}>
          Request return
        </button>
      ) : null}
      {pendingReturn ? (
        <div className="inline-form">
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Note to the student"
            maxLength={300}
          />
          <button
            type="button"
            className="btn btn-leaf btn-small"
            disabled={busy}
            onClick={() =>
              run(() => api.post(`/api/returns/${order.return_request.id}/decision`, { action: "approve", note }))
            }
          >
            Approve refund
          </button>
          <button
            type="button"
            className="btn btn-danger btn-small"
            disabled={busy}
            onClick={() =>
              run(() => api.post(`/api/returns/${order.return_request.id}/decision`, { action: "reject", note }))
            }
          >
            Reject
          </button>
        </div>
      ) : null}

      {reviewOpen ? (
        <Modal title={`Review order #${order.id}`} onClose={() => setReviewOpen(false)}>
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault();
              run(async () => {
                await api.post(`/api/orders/${order.id}/review`, { rating, comment });
                setReviewOpen(false);
                push("Review saved");
              });
            }}
          >
            <StarRating value={rating} onChange={setRating} />
            <label>
              Comment
              <textarea value={comment} onChange={(event) => setComment(event.target.value)} maxLength={500} rows={3} />
            </label>
            <button className="btn btn-primary" type="submit" disabled={busy}>
              Submit review
            </button>
          </form>
        </Modal>
      ) : null}

      {returnOpen ? (
        <Modal title={`Return order #${order.id}`} onClose={() => setReturnOpen(false)}>
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault();
              run(async () => {
                await api.post(`/api/returns/orders/${order.id}`, { reason });
                setReturnOpen(false);
                push("Return request sent");
              });
            }}
          >
            <p className="muted">Tell the kitchen what went wrong. This is a demo refund, not a real payment reversal.</p>
            <label>
              Reason
              <textarea value={reason} onChange={(event) => setReason(event.target.value)} minLength={10} maxLength={500} rows={4} required />
            </label>
            <button className="btn btn-primary" type="submit" disabled={busy}>
              Submit request
            </button>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}
