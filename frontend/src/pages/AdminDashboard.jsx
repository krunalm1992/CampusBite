import { useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import Loading from "../components/Loading";
import Modal from "../components/Modal";
import Pagination from "../components/Pagination";
import { useToast } from "../context/ToastContext";

const USER_EMPTY = { full_name: "", email: "", phone: "", password: "", role: "owner" };
const PLACE_EMPTY = {
  owner_id: "",
  name: "",
  cuisine: "",
  description: "",
  address: "",
  phone: "",
  emoji: "🍽️",
  is_active: true,
};

export default function AdminDashboard() {
  const { push } = useToast();
  const [tab, setTab] = useState("people");
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [page, setPage] = useState(1);
  const [users, setUsers] = useState(null);
  const [restaurants, setRestaurants] = useState(null);
  const [owners, setOwners] = useState([]);
  const [userForm, setUserForm] = useState(USER_EMPTY);
  const [placeForm, setPlaceForm] = useState(PLACE_EMPTY);
  const [editingPlace, setEditingPlace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setLoading(true);
    const userParams = { page, page_size: 8 };
    const placeParams = { page, page_size: 8 };
    if (tab === "people") {
      if (q.trim()) userParams.q = q.trim();
      if (role) userParams.role = role;
    } else if (q.trim()) {
      placeParams.q = q.trim();
    }
    Promise.all([api.get("/api/admin/users", { params: userParams }), api.get("/api/admin/restaurants", { params: placeParams })])
      .then(([userRes, placeRes]) => {
        setUsers(userRes.data);
        setRestaurants(placeRes.data);
      })
      .catch((err) => push(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [q, role, page, tab, tick, push]);

  useEffect(() => {
    api
      .get("/api/admin/users", { params: { role: "owner", page_size: 50 } })
      .then((response) => setOwners(response.data.items.filter((person) => person.is_active)))
      .catch(() => {});
  }, [tick]);

  async function createUser(event) {
    event.preventDefault();
    try {
      await api.post("/api/admin/users", userForm);
      setUserForm(USER_EMPTY);
      setTick((value) => value + 1);
      push("Account created");
    } catch (err) {
      push(errorMessage(err));
    }
  }

  async function toggleUser(person) {
    try {
      await api.patch(`/api/admin/users/${person.id}`, { is_active: !person.is_active });
      setTick((value) => value + 1);
    } catch (err) {
      push(errorMessage(err));
    }
  }

  async function createPlace(event) {
    event.preventDefault();
    try {
      await api.post("/api/admin/restaurants", { ...placeForm, owner_id: Number(placeForm.owner_id) });
      setPlaceForm(PLACE_EMPTY);
      setTick((value) => value + 1);
      push("Restaurant created");
    } catch (err) {
      push(errorMessage(err));
    }
  }

  async function savePlace(event) {
    event.preventDefault();
    try {
      await api.patch(`/api/admin/restaurants/${editingPlace.id}`, {
        ...editingPlace,
        owner_id: Number(editingPlace.owner_id),
      });
      setEditingPlace(null);
      setTick((value) => value + 1);
      push("Restaurant updated");
    } catch (err) {
      push(errorMessage(err));
    }
  }

  return (
    <div>
      <p className="eyebrow">Campus admin</p>
      <h1>People and kitchens</h1>
      <div className="chip-row">
        <button type="button" className={tab === "people" ? "chip on" : "chip"} onClick={() => { setTab("people"); setPage(1); }}>
          People
        </button>
        <button type="button" className={tab === "places" ? "chip on" : "chip"} onClick={() => { setTab("places"); setPage(1); }}>
          Restaurants
        </button>
      </div>

      <label className="search">
        <span className="sr">Search</span>
        <input
          value={q}
          placeholder={tab === "people" ? "Search name or email" : "Search restaurant"}
          onChange={(event) => {
            setPage(1);
            setQ(event.target.value);
          }}
        />
      </label>

      {tab === "people" ? (
        <>
          <div className="chip-row">
            {["", "customer", "owner", "delivery", "admin"].map((item) => (
              <button type="button" key={item || "all"} className={role === item ? "chip on" : "chip"} onClick={() => { setPage(1); setRole(item); }}>
                {item || "All roles"}
              </button>
            ))}
          </div>
          <form className="card form form-grid" onSubmit={createUser}>
            <h2>New account</h2>
            <label>
              Name
              <input value={userForm.full_name} onChange={(event) => setUserForm({ ...userForm, full_name: event.target.value })} required />
            </label>
            <label>
              Email
              <input type="email" value={userForm.email} onChange={(event) => setUserForm({ ...userForm, email: event.target.value })} required />
            </label>
            <label>
              Phone
              <input value={userForm.phone} onChange={(event) => setUserForm({ ...userForm, phone: event.target.value })} />
            </label>
            <label>
              Password
              <input type="password" value={userForm.password} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} required minLength={8} />
            </label>
            <label>
              Role
              <select value={userForm.role} onChange={(event) => setUserForm({ ...userForm, role: event.target.value })}>
                <option value="customer">Customer</option>
                <option value="owner">Restaurant owner</option>
                <option value="delivery">Delivery partner</option>
              </select>
            </label>
            <button className="btn btn-primary" type="submit">
              Create
            </button>
          </form>
          {loading ? <Loading /> : null}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users?.items?.map((person) => (
                  <tr key={person.id}>
                    <td>{person.full_name}</td>
                    <td>{person.email}</td>
                    <td>{person.role}</td>
                    <td>{person.is_active ? "Active" : "Inactive"}</td>
                    <td>
                      <button type="button" className="btn btn-ghost btn-small" onClick={() => toggleUser(person)}>
                        {person.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={users?.page || 1} pages={users?.pages || 0} onChange={setPage} />
        </>
      ) : (
        <>
          <form className="card form form-grid" onSubmit={createPlace}>
            <h2>New restaurant</h2>
            <label>
              Owner
              <select value={placeForm.owner_id} onChange={(event) => setPlaceForm({ ...placeForm, owner_id: event.target.value })} required>
                <option value="">Choose owner</option>
                {owners.map((owner) => (
                  <option key={owner.id} value={owner.id}>
                    {owner.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Name
              <input value={placeForm.name} onChange={(event) => setPlaceForm({ ...placeForm, name: event.target.value })} required />
            </label>
            <label>
              Cuisine
              <input value={placeForm.cuisine} onChange={(event) => setPlaceForm({ ...placeForm, cuisine: event.target.value })} />
            </label>
            <label>
              Emoji
              <input value={placeForm.emoji} onChange={(event) => setPlaceForm({ ...placeForm, emoji: event.target.value })} maxLength={8} />
            </label>
            <label>
              Phone
              <input value={placeForm.phone} onChange={(event) => setPlaceForm({ ...placeForm, phone: event.target.value })} />
            </label>
            <label>
              Address
              <input value={placeForm.address} onChange={(event) => setPlaceForm({ ...placeForm, address: event.target.value })} />
            </label>
            <label className="span-2">
              Description
              <input value={placeForm.description} onChange={(event) => setPlaceForm({ ...placeForm, description: event.target.value })} />
            </label>
            <button className="btn btn-primary" type="submit">
              Create restaurant
            </button>
          </form>
          {loading ? <Loading /> : null}
          <div className="stack">
            {restaurants?.items?.map((place) => (
              <article className="card menu-row" key={place.id}>
                <div className="card-emoji">{place.emoji}</div>
                <div>
                  <h2>{place.name}</h2>
                  <p className="muted">{place.cuisine} · {place.owner_name}</p>
                  <p className="meta">{place.is_active ? "Visible to students" : "Hidden"}</p>
                </div>
                <button type="button" className="btn btn-ghost btn-small" onClick={() => setEditingPlace({ ...place })}>
                  Edit
                </button>
              </article>
            ))}
          </div>
          <Pagination page={restaurants?.page || 1} pages={restaurants?.pages || 0} onChange={setPage} />
        </>
      )}

      {editingPlace ? (
        <Modal title="Edit restaurant" onClose={() => setEditingPlace(null)}>
          <form className="form" onSubmit={savePlace}>
            <label>
              Name
              <input value={editingPlace.name} onChange={(event) => setEditingPlace({ ...editingPlace, name: event.target.value })} required />
            </label>
            <label>
              Owner
              <select value={editingPlace.owner_id} onChange={(event) => setEditingPlace({ ...editingPlace, owner_id: event.target.value })}>
                {owners.map((owner) => (
                  <option key={owner.id} value={owner.id}>
                    {owner.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Cuisine
              <input value={editingPlace.cuisine || ""} onChange={(event) => setEditingPlace({ ...editingPlace, cuisine: event.target.value })} />
            </label>
            <label>
              Address
              <input value={editingPlace.address || ""} onChange={(event) => setEditingPlace({ ...editingPlace, address: event.target.value })} />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={editingPlace.is_active}
                onChange={(event) => setEditingPlace({ ...editingPlace, is_active: event.target.checked })}
              />
              Visible to students
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
