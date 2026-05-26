import { PropsWithChildren } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useLocation } from "react-router-dom";
import { AUTH_SETUP_QUERY_KEY, getSetupStatus } from "../api/auth";
import { useAuthStore } from "../stores/useAuth";

export function RequireAuth({ children }: PropsWithChildren) {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  // Must run for any unauthenticated visit — do not gate on hasCheckedAuth (that blocked the query
  // and left data undefined, so we fell through to /login even when needs_setup was true in cache).
  const setupQuery = useQuery({
    queryKey: AUTH_SETUP_QUERY_KEY,
    queryFn: getSetupStatus,
    enabled: !isAuthenticated,
    staleTime: 60_000,
  });

  if (!isAuthenticated) {
    if (!setupQuery.isFetched) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
          <div className="rounded-xl border border-border bg-surface px-6 py-4 text-sm text-muted shadow-panel">
            Checking access…
          </div>
        </div>
      );
    }
    if (setupQuery.isError) {
      return <Navigate to="/login" replace />;
    }
    if (setupQuery.data?.needs_setup) {
      return <Navigate to="/setup" replace />;
    }
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  }

  return <>{children}</>;
}
