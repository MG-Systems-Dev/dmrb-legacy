import { api } from "./client";
import type { AuthUser } from "../stores/useAuth";

/** React Query key for GET /auth/setup-status */
export const AUTH_SETUP_QUERY_KEY = ["setup-status"] as const;

/** @deprecated Use AUTH_SETUP_QUERY_KEY */
export const AUTH_BOOTSTRAP_QUERY_KEY = AUTH_SETUP_QUERY_KEY;

export type SetupStatus = {
  needs_setup: boolean;
  reason: string;
};

/** @deprecated Use SetupStatus */
export type BootstrapStatus = SetupStatus & {
  needs_bootstrap: boolean;
  user_count: number;
  auth_disabled: boolean;
  is_production: boolean;
  allow_api_bootstrap: boolean;
};

export async function getSetupStatus(): Promise<SetupStatus> {
  const { data } = await api.get<SetupStatus>("/auth/setup-status");
  return data;
}

/** @deprecated Use getSetupStatus */
export async function getBootstrapStatus(): Promise<SetupStatus> {
  return getSetupStatus();
}

export type SetupPayload = {
  setup_key: string;
  email: string;
  password: string;
  password_confirm: string;
};

export async function claimSetup(payload: SetupPayload): Promise<AuthUser> {
  await api.post("/auth/setup", payload);
  return getMe();
}

export type RecoveryPayload = {
  setup_key: string;
  password: string;
  password_confirm: string;
};

export async function recoveryReset(payload: RecoveryPayload): Promise<void> {
  await api.post("/auth/recovery", payload);
}

type LoginPayload = {
  email: string;
  password: string;
};

export async function login(payload: LoginPayload): Promise<AuthUser> {
  await api.post("/login", payload);
  return getMe();
}

export async function logout(): Promise<void> {
  await api.post("/logout");
}

export async function getMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>("/auth/me");
  return data;
}
