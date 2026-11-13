import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { useSocket } from "../context/SocketContext";

const ROLE_LINKS = {
  customer: [
    { to: "/orders", label: "Orders" },
    { to: "/insights", label: "Insights" },
  ],
  owner: [
    { to: "/owner", label: "Dashboard" },
    { to: "/owner/orders", label: "Orders" },
    { to: "/owner/menu", label: "Menu" },
  ],
  delivery: [{ to: "/delivery", label: "Deliveries" }],
  admin: [{ to: "/admin", label: "Admin" }],
};

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const { connected } = useSocket();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const links = user ? ROLE_LINKS[user.role] || [] : [];

  function closeAnd(path) {
    setOpen(false);
    if (path) navigate(path);
  }

  return (
    <div className="app">
      <header className="nav">
        <div className="nav-inner">
          <Link to="/" className="brand" onClick={() => setOpen(false)}>
            <span className="brand-mark">C</span>
            CampusBite
          </Link>
          <button type="button" className="nav-toggle" aria-label="Menu" onClick={() => setOpen((value) => !value)}>
            Menu
          </button>
          <nav className={open ? "nav-links open" : "nav-links"}>
            <NavLink to="/" end onClick={() => setOpen(false)}>
              Restaurants
            </NavLink>
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} end={true} onClick={() => setOpen(false)}>
                {link.label}
              </NavLink>
            ))}
            {user?.role === "customer" ? (
              <NavLink to="/cart" onClick={() => setOpen(false)} className="cart-link">
                Cart
                {count ? <span className="count">{count}</span> : null}
              </NavLink>
            ) : null}
            {user ? (
              <div className="user-chip">
                {connected ? <span className="live-dot" title="Live updates on" /> : null}
                <span>{user.full_name.split(" ")[0]}</span>
                <button
                  type="button"
                  className="btn btn-ghost btn-small"
                  onClick={() => {
                    logout();
                    closeAnd("/login");
                  }}
                >
                  Log out
                </button>
              </div>
            ) : (
              <div className="user-chip">
                <NavLink to="/login" onClick={() => setOpen(false)}>
                  Log in
                </NavLink>
                <NavLink to="/register" className="btn btn-primary btn-small" onClick={() => setOpen(false)}>
                  Register
                </NavLink>
              </div>
            )}
          </nav>
        </div>
      </header>
      <main className="page">{children}</main>
      <footer className="footer">
        <span>CampusBite</span>
        <span>Order between lectures. Dummy payments only.</span>
      </footer>
    </div>
  );
}
