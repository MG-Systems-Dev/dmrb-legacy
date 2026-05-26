import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { recoveryReset } from "../api/auth";

const MIN_PASSWORD = 12;

export function RecoveryPage() {
  const navigate = useNavigate();

  const [setupKey, setSetupKey] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const mutation = useMutation({
    mutationFn: recoveryReset,
    onSuccess: () => {
      toast.success("Password reset. Please sign in.");
      navigate("/login", { replace: true });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Recovery failed");
    },
  });

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!setupKey.trim()) errors.setupKey = "Setup key is required.";
    if (password.length < MIN_PASSWORD) {
      errors.password = `Password must be at least ${MIN_PASSWORD} characters.`;
    }
    if (password !== passwordConfirm) {
      errors.passwordConfirm = "Passwords do not match.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validate()) return;
    mutation.mutate({
      setup_key: setupKey.trim(),
      password,
      password_confirm: passwordConfirm,
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-panel">
        <p className="text-[11px] font-medium uppercase tracking-[0.24em] text-muted">DMRB</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-text-strong">
          Reset admin password
        </h1>
        <p className="mt-2 text-sm text-muted">
          Enter your setup key and choose a new password for the admin account.
        </p>

        <form className="mt-8 space-y-4" onSubmit={handleSubmit} noValidate>
          <div>
            <label className="block">
              <span className="label">Setup key</span>
              <input
                type="password"
                value={setupKey}
                onChange={(e) => setSetupKey(e.target.value)}
                className="input"
                autoComplete="off"
                required
              />
            </label>
            {fieldErrors.setupKey && (
              <p className="mt-1 text-xs text-red-400">{fieldErrors.setupKey}</p>
            )}
          </div>

          <div>
            <label className="block">
              <span className="label">New password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                autoComplete="new-password"
                minLength={MIN_PASSWORD}
                required
              />
            </label>
            {fieldErrors.password && (
              <p className="mt-1 text-xs text-red-400">{fieldErrors.password}</p>
            )}
          </div>

          <div>
            <label className="block">
              <span className="label">Confirm new password</span>
              <input
                type="password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                className="input"
                autoComplete="new-password"
                minLength={MIN_PASSWORD}
                required
              />
            </label>
            {fieldErrors.passwordConfirm && (
              <p className="mt-1 text-xs text-red-400">{fieldErrors.passwordConfirm}</p>
            )}
          </div>

          <p className="text-xs text-muted">Minimum {MIN_PASSWORD} characters.</p>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="btn-primary w-full"
          >
            {mutation.isPending ? "Resetting…" : "Reset password"}
          </button>

          <p className="text-center text-xs text-muted">
            Remembered your password?{" "}
            <a href="/login" className="text-text underline underline-offset-2">
              Sign in
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}
