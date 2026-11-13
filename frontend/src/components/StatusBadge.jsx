import { label } from "../utils/format";

export default function StatusBadge({ status }) {
  if (!status) return null;
  return (
    <span className="badge" data-status={status}>
      {label(status)}
    </span>
  );
}
