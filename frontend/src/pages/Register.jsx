import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register, user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  function setField(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(form);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form auth-narrow" onSubmit={onSubmit}>
      <p className="eyebrow">Student account</p>
      <h1>Create your CampusBite login</h1>
      <p className="muted">Kitchen and delivery accounts are issued by campus admin.</p>
      <label>
        Full name
        <input value={form.full_name} onChange={(event) => setField("full_name", event.target.value)} required minLength={2} />
      </label>
      <label>
        Email
        <input type="email" value={form.email} onChange={(event) => setField("email", event.target.value)} required />
      </label>
      <label>
        Phone
        <input value={form.phone} onChange={(event) => setField("phone", event.target.value)} maxLength={20} />
      </label>
      <label>
        Password
        <input type="password" value={form.password} onChange={(event) => setField("password", event.target.value)} required minLength={8} />
      </label>
      {error ? <p className="error-text">{error}</p> : null}
      <button className="btn btn-primary" type="submit" disabled={busy}>
        {busy ? "Creating..." : "Create account"}
      </button>
      <p className="muted">
        Already registered? <Link to="/login">Log in</Link>
      </p>
    </form>
  );
}
