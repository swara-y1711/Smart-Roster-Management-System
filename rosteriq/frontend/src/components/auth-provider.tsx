"use client";

import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { Session, User } from "@supabase/supabase-js";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import type { Database } from "@/lib/supabase/database.types";

export type ManagerProfile = Database["public"]["Tables"]["manager_profiles"]["Row"];

type AuthContextValue = {
  client: ReturnType<typeof getSupabaseBrowserClient>;
  user: User | null;
  profile: ManagerProfile | null;
  isLoading: boolean;
  profileError: string;
  refreshProfile: (userId: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useMemo(() => getSupabaseBrowserClient(), []);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(() => Boolean(client));
  const [profile, setProfile] = useState<ManagerProfile | null>(null);
  const [profileError, setProfileError] = useState("");
  const currentUserId = useRef<string | null>(null);

  const refreshProfile = useCallback(
    async (userId: string) => {
      if (!client) {
        return;
      }

      try {
        const { data, error } = await client
          .from("manager_profiles")
          .select("id, full_name, work_email, employee_id, created_at")
          .eq("id", userId)
          .maybeSingle();
        const {
          data: { session: currentSession },
        } = await client.auth.getSession();
        if (currentSession?.user.id === userId) {
          setProfile(data);
          setProfileError(error?.message ?? "");
        }
      } catch (error: unknown) {
        setProfileError(
          error instanceof Error ? error.message : "Unable to retrieve your manager profile.",
        );
      }
    },
    [client],
  );

  useEffect(() => {
    if (!client) {
      return;
    }

    let active = true;
    function updateSession(nextSession: Session | null) {
      const nextUserId = nextSession?.user.id ?? null;
      const userChanged = currentUserId.current !== nextUserId;
      if (userChanged) {
        currentUserId.current = nextUserId;
        setProfile(null);
        setProfileError("");
      }
      setSession(nextSession);
      setIsLoading(false);
      return userChanged;
    }

    const {
      data: { subscription },
    } = client.auth.onAuthStateChange((_event, nextSession) => {
      if (active) {
        const userChanged = updateSession(nextSession);
        if (userChanged && nextSession) {
          window.setTimeout(() => {
            if (active) {
              void refreshProfile(nextSession.user.id);
            }
          }, 0);
        }
      }
    });

    void client.auth.getSession().then(({ data, error }) => {
      if (!active) {
        return;
      }
      const userChanged = updateSession(data.session);
      if (userChanged && data.session) {
        void refreshProfile(data.session.user.id);
      }
      if (error) {
        setProfileError(error.message);
      }
    }).catch((error: unknown) => {
      if (active) {
        setProfileError(
          error instanceof Error ? error.message : "Unable to restore your Supabase session.",
        );
        setIsLoading(false);
      }
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [client, refreshProfile]);

  const value = useMemo(
    () => ({
      client,
      user: session?.user ?? null,
      profile,
      isLoading,
      profileError,
      refreshProfile,
    }),
    [client, isLoading, profile, profileError, refreshProfile, session?.user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
