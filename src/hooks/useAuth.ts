import { useEffect, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";

export function mt5LoginToEmail(login: string) {
  return `${login.trim()}@traderpanel.local`;
}

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    const guestUserStr = localStorage.getItem("guest_user");
    if (guestUserStr) {
      try {
        const parsedUser = JSON.parse(guestUserStr);
        setUser(parsedUser);
        setSession({
          access_token: "guest",
          token_type: "bearer",
          expires_in: 999999,
          refresh_token: "guest",
          user: parsedUser,
        });
        setLoading(false);
        return;
      } catch (e) {
        localStorage.removeItem("guest_user");
      }
    }

    const { data } = await supabase.auth.getSession();
    setSession(data.session);
    setUser(data.session?.user ?? null);
    setLoading(false);
  };

  useEffect(() => {
    checkAuth();

    const { data: sub } = supabase.auth.onAuthStateChange((_evt, s) => {
      if (s) {
        localStorage.removeItem("guest_user");
      }
      checkAuth();
    });

    const handleAuthChange = () => {
      checkAuth();
    };

    window.addEventListener("auth-change", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

    return () => {
      sub.subscription.unsubscribe();
      window.removeEventListener("auth-change", handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, []);

  const loginAsGuest = () => {
    const parsedUser: User = {
      id: "guest",
      email: "guest@traderpanel.local",
      app_metadata: {},
      user_metadata: { mt5_login: "Mehmon", mt5_server: "MetaQuotes-Demo" },
      aud: "authenticated",
      created_at: new Date().toISOString(),
    };
    localStorage.setItem("guest_user", JSON.stringify(parsedUser));
    window.dispatchEvent(new Event("auth-change"));
  };

  const logout = async () => {
    localStorage.removeItem("guest_has_visited");
    sessionStorage.removeItem("guest_session_redirected");
    if (localStorage.getItem("guest_user")) {
      localStorage.removeItem("guest_user");
      window.dispatchEvent(new Event("auth-change"));
    } else {
      await supabase.auth.signOut();
    }
  };

  return { session, user, loading, loginAsGuest, logout, isGuest: user?.id === "guest" };
}

