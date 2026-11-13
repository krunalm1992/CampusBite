import { useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import EmptyState from "../components/EmptyState";
import Loading from "../components/Loading";
import Modal from "../components/Modal";
import Pagination from "../components/Pagination";
import { useToast } from "../context/ToastContext";
import { money } from "../utils/format";

const EMPTY = { name: "", description: "", category: "Mains", price: "", emoji: "🍽️", is_available: true };

export default function MenuManage() {
  const { push } = useToast();
  const [restaurants, setRestaurants] = useState([]);
  const [restaurantId, setRestaurantId] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/api/owner/restaurants")
      .then((response) => {
        setRestaurants(response.data);
        if (response.data[0]) setRestaurantId(String(response.data[0].id));
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(() => {
    if (!restaurantId) return;
    setLoading(true);
    api
      .get("/api/menu", { params: { restaurant_id: restaurantId, page, page_size: 10 } })
      .then((response) => setData(response.data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [restaurantId, page]);

  function reload() {
    setPage(1);
    return api.get("/api/menu", { params: { restaurant_id: restaurantId, page: 1, page_size: 10 } }).then((response) => setData(response.data));
  }

  async function createDish(event) {
    event.preventDefault();
    try {
      await api.post(`/api/menu/restaurants/${restaurantId}`, {
        ...form,
        price: Number(form.price),
      });
      setForm(EMPTY);
      await reload();
      push("Dish added");
    } catch (err) {
      push(errorMessage(err));
    }
  }

  async function saveEdit(event) {
    event.preventDefault();
    try {
      await api.put(`/api/menu/${editing.id}`, { ...editing, price: Number(editing.price) });
      setEditing(null);
      await reload();
      push("Dish updated");
    } catch (err) {
      push(errorMessage(err));
    }
  }

  async function toggle(dish) {
    try {
      await api.patch(`/api/menu/${dish.id}/availability`, { is_available: !dish.is_available });
      await reload();
    } catch (err) {
      push(errorMessage(err));
    }
  }

  async function remove(dish) {
    if (!window.confirm(`Remove ${dish.name} from the menu?`)) return;
    try {
      await api.delete(`/api/menu/${dish.id}`);
      await reload();
    } catch (err) {
      push(errorMessage(err));
    }
  }

  if (error && !restaurants.length) return <p className="error-text">{error}</p>;

  return (
    <div>
      <div className="dashboard-head">
        <div>
          <p className="eyebrow">Menu</p>
          <h1>Dishes</h1>
        </div>
        {restaurants.length > 1 ? (
          <label>
            Restaurant
            <select
              value={restaurantId}
              onChange={(event) => {
                setPage(1);
                setRestaurantId(event.target.value);
              }}
            >
              {restaurants.map((restaurant) => (
                <option key={restaurant.id} value={restaurant.id}>
                  {restaurant.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <form className="card form form-grid" onSubmit={createDish}>
        <h2>Add a dish</h2>
        <label>
          Name
          <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required minLength={2} />
        </label>
        <label>
          Price (₹)
          <input type="number" min="1" step="1" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} required />
        </label>
        <label>
          Category
          <input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} />
        </label>
        <label>
          Emoji
          <input value={form.emoji} onChange={(event) => setForm({ ...form, emoji: event.target.value })} maxLength={8} />
        </label>
        <label className="span-2">
          Description
          <input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        </label>
        <button className="btn btn-primary" type="submit">
          Add dish
        </button>
      </form>

      {loading ? <Loading /> : null}
      {!loading && data?.items?.length === 0 ? <EmptyState title="No dishes yet" text="Add the first item above." /> : null}
      <div className="stack">
        {data?.items?.map((dish) => (
          <article className="card menu-row" key={dish.id}>
            <div className="card-emoji">{dish.emoji}</div>
            <div>
              <p className="eyebrow">{dish.category}</p>
              <h2>{dish.name}</h2>
              <p className="muted">{dish.description}</p>
              <p className="meta">{dish.is_available ? "Available" : "Hidden from students"}</p>
            </div>
            <div className="menu-buy">
              <strong>{money(dish.price)}</strong>
              <button type="button" className="btn btn-ghost btn-small" onClick={() => toggle(dish)}>
                {dish.is_available ? "Mark unavailable" : "Mark available"}
              </button>
              <button type="button" className="btn btn-ghost btn-small" onClick={() => setEditing({ ...dish })}>
                Edit
              </button>
              <button type="button" className="btn btn-danger btn-small" onClick={() => remove(dish)}>
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>
      <Pagination page={data?.page || 1} pages={data?.pages || 0} onChange={setPage} />

      {editing ? (
        <Modal title="Edit dish" onClose={() => setEditing(null)}>
          <form className="form" onSubmit={saveEdit}>
            <label>
              Name
              <input value={editing.name} onChange={(event) => setEditing({ ...editing, name: event.target.value })} required />
            </label>
            <label>
              Price
              <input type="number" min="1" value={editing.price} onChange={(event) => setEditing({ ...editing, price: event.target.value })} required />
            </label>
            <label>
              Category
              <input value={editing.category} onChange={(event) => setEditing({ ...editing, category: event.target.value })} />
            </label>
            <label>
              Description
              <textarea value={editing.description || ""} onChange={(event) => setEditing({ ...editing, description: event.target.value })} rows={3} />
            </label>
            <button className="btn btn-primary" type="submit">
              Save
            </button>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}
