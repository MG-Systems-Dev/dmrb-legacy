import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AUTH_SETUP_QUERY_KEY, getSetupStatus, getMe } from "./api/auth";
import { router } from "./router";
import { useAuthStore } from "./stores/useAuth";

function AuthBootstrap() {
  const setSession = useAuthStore((state) => state.setSession);
  const clearSession = useAuthStore((state) => state.clearSession);

  const setupQuery = useQuery({
    queryKey: AUTH_SETUP_QUERY_KEY,
    queryFn: getSetupStatus,
  });

  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: getMe,
    enabled: Boolean(setupQuery.isSuccess && !setupQuery.data?.needs_setup),
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!setupQuery.isSuccess) {
      return;
    }
    if (setupQuery.data?.needs_setup) {
      clearSession();
    }
  }, [setupQuery.isSuccess, setupQuery.data?.needs_setup, clearSession]);

  useEffect(() => {
    if (setupQuery.isError) {
      clearSession();
    }
  }, [setupQuery.isError, clearSession]);

  useEffect(() => {
    if (!setupQuery.isSuccess || setupQuery.data?.needs_setup) {
      return;
    }
    if (meQuery.data) {
      setSession({ user: meQuery.data });
    } else if (meQuery.isError) {
      clearSession();
    }
  }, [
    setupQuery.isSuccess,
    setupQuery.data?.needs_setup,
    meQuery.data,
    meQuery.isError,
    setSession,
    clearSession,
  ]);

  return <RouterProvider router={router} />;
}

export default function App() {
  return <AuthBootstrap />;
}
