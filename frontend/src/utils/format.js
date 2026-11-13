export const STATUSES = [
  "PLACED",
  "ACCEPTED",
  "PREPARING",
  "READY",
  "ASSIGNED",
  "OUT_FOR_DELIVERY",
  "DELIVERED",
  "CANCELLED",
  "REFUNDED",
];

const LABELS = {
  PLACED: "Placed",
  ACCEPTED: "Accepted",
  PREPARING: "Preparing",
  READY: "Ready",
  ASSIGNED: "Assigned",
  OUT_FOR_DELIVERY: "Out for delivery",
  DELIVERED: "Delivered",
  CANCELLED: "Cancelled",
  REFUNDED: "Refunded",
  mock_paid: "Paid (demo)",
  refunded: "Refunded",
  pending: "Return pending",
  approved: "Return approved",
  rejected: "Return rejected",
};

export function label(value) {
  return LABELS[value] || value;
}

export function money(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
}

export function when(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function homeFor(role) {
  if (role === "owner") return "/owner";
  if (role === "delivery") return "/delivery";
  if (role === "admin") return "/admin";
  return "/";
}
