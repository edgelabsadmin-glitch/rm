import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { clientApi, clearClientSession, getClientSession, setClientSession, type ClientMe } from "@/lib/client-api";

interface ClientAuthValue {
  me: ClientMe | null;
  loading: boolean;
  login: (sessionId: string) => Promise<void>;
  logout: () => Promise<void>;
}

const ClientAuthContext = createContext<ClientAuthValue | null>(null);

export function ClientAuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<ClientMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getClientSession()) {
      setLoading(false);
      return;
    }
    clientApi
      .me()
      .then(setMe)
      .catch(() => {
        clearClientSession();
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (sessionId: string) => {
    setClientSession(sessionId);
    const data = await clientApi.me();
    setMe(data);
  }, []);

  const logout = useCallback(async () => {
    await clientApi.logout().catch(() => {});
    clearClientSession();
    setMe(null);
    window.location.href = "/client/login";
  }, []);

  return (
    <ClientAuthContext.Provider value={{ me, loading, login, logout }}>
      {children}
    </ClientAuthContext.Provider>
  );
}

export function useClientAuth() {
  const ctx = useContext(ClientAuthContext);
  if (!ctx) throw new Error("useClientAuth must be used inside ClientAuthProvider");
  return ctx;
}
