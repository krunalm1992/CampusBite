import axios from "axios";

export const TOKEN_KEY = "campusbite_token";
export const CART_KEY = "campusbite_cart";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = error?.config?.url || "";
    // A failed login should stay on the form. Any other 401 means the stored token is dead.
    if (status === 401 && !url.includes("/api/auth/login") && !url.includes("/api/auth/register")) {
      localStorage.removeItem(TOKEN_KEY);
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  }
);

export function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(" ");
  }
  return "Something went wrong. Please try again.";
}

export default api;
