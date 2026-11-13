import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { homeFor } from "../utils/format";

const DEMOS = [
  ["Student", "customer@campusbite.com", "Customer@123"],
  ["Kitchen", "owner@campusbite.com", "Owner@123"],
  ["Delivery", "delivery@campusbite.com", "Delivery@123"],
  ["Admin", "admin@campusbite.com", "Admin@123"],
];

export default function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const signedIn = await login(email, password);
      navigate(homeFor(signedIn.role), { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-layout">
      <form className="card form" onSubmit={onSubmit}>
        <p className="eyebrow">Welcome back</p>
        <h1>Log in</h1>
        <label>
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" />
        </label>
        {error ? <p className="error-text">{error}</p> : null}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Checking..." : "Log in"}
        </button>
        <p className="muted">
          New here? <Link to="/register">Create a student account</Link>
        </p>
      </form>
      <aside className="card demo-accounts">
        <h2>Demo accounts</h2>
        <p className="muted">Seeded when the database is empty. Click a row to fill the form.</p>
        {DEMOS.map(([role, demoEmail, demoPassword]) => (
          <button
            type="button"
            key={demoEmail}
            className="demo-row"
            onClick={() => {
              setEmail(demoEmail);
              setPassword(demoPassword);
            }}
          >
            <strong>{role}</strong>
            <span>{demoEmail}</span>
            <span>{demoPassword}</span>
          </button>
        ))}
      </aside>
    </div>
  );
}
