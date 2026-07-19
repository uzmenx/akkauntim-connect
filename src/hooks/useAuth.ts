import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // LocalStorage orqali foydalanuvchining login holatini tekshiramiz
    const savedLogin = localStorage.getItem("mt5_login");
    if (savedLogin) {
      setUser({
        id: "00000000-0000-0000-0000-000000000000",
        email: `${savedLogin}@mt5.bot`,
      } as User);
    } else {
      setUser(null);
    }
    setLoading(false);
  }, []);

  const loginLocal = (mt5Login: string) => {
    localStorage.setItem("mt5_login", mt5Login);
    setUser({
      id: "00000000-0000-0000-0000-000000000000",
      email: `${mt5Login}@mt5.bot`,
    } as User);
  };

  const logoutLocal = () => {
    localStorage.removeItem("mt5_login");
    setUser(null);
  };

  return { 
    session: null, 
    user, 
    loading, 
    loginLocal, 
    logoutLocal 
  };
}
