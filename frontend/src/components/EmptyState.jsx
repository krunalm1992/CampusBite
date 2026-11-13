export default function EmptyState({ title, text, children }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {text ? <p>{text}</p> : null}
      {children}
    </div>
  );
}
