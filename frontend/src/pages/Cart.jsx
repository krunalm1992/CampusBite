import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import { useCart } from "../context/CartContext";
import { money } from "../utils/format";

export default function Cart() {
  const { items, setQuantity, removeItem, total } = useCart();

  if (!items.length) {
    return (
      <EmptyState title="Your cart is empty" text="Pick a kitchen and add a dish.">
        <Link to="/" className="btn btn-primary">
          Browse restaurants
        </Link>
      </EmptyState>
    );
  }

  return (
    <div className="split">
      <section>
        <h1>Cart</h1>
        <p className="muted">From {items[0].restaurantName}. Checkout uses a dummy payment.</p>
        <div className="stack">
          {items.map((item) => (
            <article className="card menu-row" key={item.menuItemId}>
              <div className="card-emoji">{item.emoji}</div>
              <div>
                <h2>{item.name}</h2>
                <p className="muted">{money(item.price)} each</p>
              </div>
              <div className="menu-buy">
                <strong>{money(item.price * item.quantity)}</strong>
                <div className="qty">
                  <button type="button" onClick={() => setQuantity(item.menuItemId, item.quantity - 1)} aria-label="Decrease">
                    −
                  </button>
                  <span>{item.quantity}</span>
                  <button type="button" onClick={() => setQuantity(item.menuItemId, Math.min(20, item.quantity + 1))} aria-label="Increase">
                    +
                  </button>
                </div>
                <button type="button" className="btn btn-ghost btn-small" onClick={() => removeItem(item.menuItemId)}>
                  Remove
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
      <aside className="card summary">
        <h2>Total</h2>
        <p className="price-lg">{money(total)}</p>
        <p className="muted">The kitchen price is confirmed again when you place the order.</p>
        <Link to="/checkout" className="btn btn-primary">
          Checkout
        </Link>
      </aside>
    </div>
  );
}
