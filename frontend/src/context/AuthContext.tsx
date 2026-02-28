import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { login as apiLogin, register as apiRegister } from "../api/auth";
import { setToken } from "../api/client";

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthContextValue {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    const { access_token } = await apiLogin(username, password);
    setToken(access_token);
    // Decode sub from JWT (base64) to get user id
    const payload = JSON.parse(atob(access_token.split(".")[1]));
    setUser({ id: payload.sub, username, email: "" });
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      const registeredUser = await apiRegister(username, email, password);
      // Auto-login after registration
      const { access_token } = await apiLogin(username, password);
      setToken(access_token);
      setUser({
        id: registeredUser.id,
        username: registeredUser.username,
        email: registeredUser.email,
      });
    },
    []
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
