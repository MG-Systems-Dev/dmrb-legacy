import { FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate, Navigate } from "react-router-dom";
import { toast } from "sonner";
import { AUTH_SETUP_QUERY_KEY, getSetupStatus, login } from "../api/auth";
import { useAuthStore } from "../stores/useAuth";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((state) => state.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const setupQuery = useQuery({
    queryKey: AUTH_SETUP_QUERY_KEY,
    queryFn: getSetupStatus,
    staleTime: 30_000,
  });

  const search = new URLSearchParams(location.search);
  const next = search.get("next") ?? "/board";

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: (user) => {
      setSession({ user });
      toast.success("Signed in");
      navigate(next, { replace: true });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Invalid email or password");
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.mutate({ email: email.trim().toLowerCase(), password });
  };

  if (setupQuery.data?.needs_setup) {
    return <Navigate to="/setup" replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-panel">
        <p className="text-[11px] font-medium uppercase tracking-[0.24em] text-muted">
          DMRB
        </p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-text-strong">
          Sign in
        </h1>
        <p className="mt-2 text-sm text-muted">Sign in to continue.</p>

        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="label">Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="input"
              autoComplete="email"
              required
            />
          </label>
          <label className="block">
            <span className="label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="input"
              autoComplete="current-password"
              required
            />
          </label>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="btn-primary w-full"
          >
            {mutation.isPending ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-muted">
          Locked out?{" "}
          <a href="/recovery" className="text-text underline underline-offset-2">
            Reset admin password
          </a>
        </p>
      </div>
    </div>
  );
}
