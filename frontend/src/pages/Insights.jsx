import { useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import Loading from "../components/Loading";
import { money, when, label } from "../utils/format";

const PROMPTS = [
  "Summarize my last five orders.",
  "Which of my orders are still not delivered?",
  "How much did I spend this week?",
  "Which food items have I ordered most frequently?",
];

export default function Insights() {
  const [snapshot, setSnapshot] = useState(null);
  const [question, setQuestion] = useState(PROMPTS[0]);
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/api/ai/snapshot").then((response) => setSnapshot(response.data)).catch((err) => setError(errorMessage(err)));
  }, []);

  async function ask(event) {
    event?.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await api.post("/api/ai/insights", { question });
      setAnswer(response.data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p className="eyebrow">Order insights</p>
      <h1>Ask about your own orders.</h1>
      <p className="lede">Questions are answered from your history only. Another student's orders are never included.</p>

      {!snapshot ? <Loading /> : (
        <div className="stats">
          <article className="stat">
            <span>Orders in view</span>
            <strong>{snapshot.order_count}</strong>
          </article>
          <article className="stat">
            <span>Still open</span>
            <strong>{snapshot.open_count}</strong>
          </article>
          <article className="stat">
            <span>Spent this week</span>
            <strong>{money(snapshot.spend_this_week)}</strong>
          </article>
          <article className="stat">
            <span>Most ordered</span>
            <strong>{snapshot.top_items[0] ? snapshot.top_items[0].name : "—"}</strong>
          </article>
        </div>
      )}

      <div className="chip-row">
        {PROMPTS.map((prompt) => (
          <button type="button" key={prompt} className={question === prompt ? "chip on" : "chip"} onClick={() => setQuestion(prompt)}>
            {prompt}
          </button>
        ))}
      </div>

      <form className="card form" onSubmit={ask}>
        <label>
          Question
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={3} minLength={3} maxLength={500} required />
        </label>
        {error ? <p className="error-text">{error}</p> : null}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Thinking..." : "Ask"}
        </button>
        {answer ? (
          <div className="answer">
            <p className="eyebrow">{answer.source === "openai" ? "OpenAI" : "Local summary"}</p>
            <p>{answer.answer}</p>
          </div>
        ) : null}
      </form>

      {snapshot?.last_five?.length ? (
        <section className="section">
          <h2>Last five</h2>
          <div className="stack">
            {snapshot.last_five.map((order) => (
              <article className="card compact" key={order.id}>
                <strong>#{order.id}</strong> {order.restaurant}
                <span className="meta">
                  {label(order.status)} · {money(order.total_amount)} · {when(order.created_at)}
                </span>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
