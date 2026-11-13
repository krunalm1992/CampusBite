import { createContext, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { useToast } from "./ToastContext";

const SocketContext = createContext({ connected: false, lastEvent: null });

function socketUrl(token) {
  const base = import.meta.env.VITE_API_URL || window.location.origin;
  const url = new URL("/api/ws", base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("token", token);
  return url.toString();
}

export function SocketProvider({ children }) {
  const { token, user } = useAuth();
  const { push } = useToast();
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);

  useEffect(() => {
    if (!token || !user) {
      setConnected(false);
      return undefined;
    }
    let socket;
    let retry;
    let stopped = false;

    const connect = () => {
      socket = new WebSocket(socketUrl(token));
      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch {
          return;
        }
        if (data.type === "connected" || data.type === "pong") return;
        setLastEvent({ ...data, receivedAt: Date.now() });
        if (data.message) push(data.message);
      };
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) retry = setTimeout(connect, 3000);
      };
    };

    connect();
    const ping = setInterval(() => {
      if (socket && socket.readyState === WebSocket.OPEN) socket.send("ping");
    }, 25000);

    return () => {
      stopped = true;
      clearTimeout(retry);
      clearInterval(ping);
      socket?.close();
    };
  }, [token, user, push]);

  return <SocketContext.Provider value={{ connected, lastEvent }}>{children}</SocketContext.Provider>;
}

export function useSocket() {
  return useContext(SocketContext);
}
