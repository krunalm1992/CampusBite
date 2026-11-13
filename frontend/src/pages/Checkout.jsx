import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { useCart } from "../context/CartContext";
import { money } from "../utils/format";

export default function Checkout() {
  const { items, total, clear } = useCart();
  const navigate = useNavigate();
  const [address, setAddress] = useState("Hostel 4, Room 212, Campus North");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!items.length) {
    return (
      <p>
        Your cart is empty. <Link to="/">Browse restaurants</Link>
      </p>
    );
  }

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await api.post("/api/orders", {
        restaurant_id: items[0].restaurantId,
        delivery_address: address,
        notes: notes || null,
        items: items.map((item) => ({ menu_item_id: item.menuItemId, quantity: item.quantity })),
      });
      clear();
      navigate(`/orders/${response.data.id}`, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="split">
      <form className="card form" onSubmit={onSubmit}>
        <p className="eyebrow">Dummy payment</p>
        <h1>Place order</h1>
        <p className="muted">
          No card is charged. CampusBite records a mock payment as soon as the order is placed.
        </p>
        <label>
          Delivery spot
          <input value={address} onChange={(event) => setAddress(event.target.value)} required minLength={5} maxLength={255} />
        </label>
        <label>
          Note for the kitchen
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={300} rows={3} />
        </label>
        {error ? <p className="error-text">{error}</p> : null}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Placing..." : `Pay ${money(total)} and place order`}
        </button>
      </form>
      <aside className="card summary">
        <h2>{items[0].restaurantName}</h2>
        <ul className="plain-list">
          {items.map((item) => (
            <li key={item.menuItemId}>
              <span>
                {item.quantity} × {item.name}
              </span>
              <span>{money(item.price * item.quantity)}</span>
            </li>
          ))}
        </ul>
        <p className="price-lg">{money(total)}</p>
      </aside>
    </div>
  );
}
