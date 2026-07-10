import { createContext, useContext, useState, type ReactNode } from "react";

// Minimal client-side role model mirroring the backend (§6): an operator holds
// a bearer token (write access); without one you're a read-only client. The
// token is kept in localStorage so a refresh doesn't drop the operator session.
interface Session {
  token: string | null;
  isOperator: boolean;
  signIn: (token: string) => void;
  signOut: () => void;
  // Bumped after an operator mutation so data views know to refetch.
  dataVersion: number;
  refresh: () => void;
}

const Ctx = createContext<Session | null>(null);
const KEY = "impactdesk.token";

export function SessionProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(KEY));
  const [dataVersion, setDataVersion] = useState(0);

  const signIn = (t: string) => {
    localStorage.setItem(KEY, t);
    setToken(t);
  };
  const signOut = () => {
    localStorage.removeItem(KEY);
    setToken(null);
  };
  const refresh = () => setDataVersion((v) => v + 1);

  return (
    <Ctx.Provider value={{ token, isOperator: !!token, signIn, signOut, dataVersion, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useSession(): Session {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession must be used within SessionProvider");
  return s;
}
