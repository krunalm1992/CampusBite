import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { CART_KEY } from "../api/client";

const CartContext = createContext(null);

function readCart() {
  try {
    const raw = localStorage.getItem(CART_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function CartProvider({ children }) {
  const [items, setItems] = useState(readCart);

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
  }, [items]);

  useEffect(() => {
    const clear = () => setItems([]);
    window.addEventListener("cb:cart-clear", clear);
    return () => window.removeEventListener("cb:cart-clear", clear);
  }, []);

  const value = useMemo(() => {
    // One restaurant per cart. A campus runner picks up from a single kitchen.
    function addItem(item) {
      if (items.length && items[0].restaurantId !== item.restaurantId) {
        const replace = window.confirm("Your cart has dishes from another restaurant. Replace the cart?");
        if (!replace) return false;
        setItems([{ ...item, quantity: 1 }]);
        return true;
      }
      setItems((current) => {
        const existing = current.find((row) => row.menuItemId === item.menuItemId);
        if (!existing) return [...current, { ...item, quantity: 1 }];
        return current.map((row) =>
          row.menuItemId === item.menuItemId ? { ...row, quantity: Math.min(row.quantity + 1, 20) } : row
        );
      });
      return true;
    }

    function setQuantity(menuItemId, quantity) {
      setItems((current) =>
        current
          .map((row) => (row.menuItemId === menuItemId ? { ...row, quantity } : row))
          .filter((row) => row.quantity > 0)
      );
    }

    function removeItem(menuItemId) {
      setItems((current) => current.filter((row) => row.menuItemId !== menuItemId));
    }

    function clear() {
      setItems([]);
    }

    const count = items.reduce((sum, row) => sum + row.quantity, 0);
    const total = items.reduce((sum, row) => sum + row.price * row.quantity, 0);
    return { items, addItem, setQuantity, removeItem, clear, count, total };
  }, [items]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  return useContext(CartContext);
}
