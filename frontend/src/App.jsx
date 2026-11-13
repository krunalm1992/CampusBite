import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminDashboard from "./pages/AdminDashboard";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import CustomerOrders from "./pages/CustomerOrders";
import DeliveryDashboard from "./pages/DeliveryDashboard";
import Home from "./pages/Home";
import Insights from "./pages/Insights";
import Login from "./pages/Login";
import MenuManage from "./pages/MenuManage";
import MenuPage from "./pages/MenuPage";
import OrderDetail from "./pages/OrderDetail";
import OwnerDashboard from "./pages/OwnerDashboard";
import OwnerOrders from "./pages/OwnerOrders";
import Register from "./pages/Register";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/restaurants/:id" element={<MenuPage />} />
        <Route path="/cart" element={<ProtectedRoute roles={["customer"]}><Cart /></ProtectedRoute>} />
        <Route path="/checkout" element={<ProtectedRoute roles={["customer"]}><Checkout /></ProtectedRoute>} />
        <Route path="/orders" element={<ProtectedRoute roles={["customer"]}><CustomerOrders /></ProtectedRoute>} />
        <Route path="/orders/:id" element={<ProtectedRoute roles={["customer", "owner", "delivery"]}><OrderDetail /></ProtectedRoute>} />
        <Route path="/insights" element={<ProtectedRoute roles={["customer"]}><Insights /></ProtectedRoute>} />
        <Route path="/owner" element={<ProtectedRoute roles={["owner"]}><OwnerDashboard /></ProtectedRoute>} />
        <Route path="/owner/orders" element={<ProtectedRoute roles={["owner"]}><OwnerOrders /></ProtectedRoute>} />
        <Route path="/owner/menu" element={<ProtectedRoute roles={["owner"]}><MenuManage /></ProtectedRoute>} />
        <Route path="/delivery" element={<ProtectedRoute roles={["delivery"]}><DeliveryDashboard /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute roles={["admin"]}><AdminDashboard /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
