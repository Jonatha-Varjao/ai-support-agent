import { apiFetch, ApiError } from "./client";

export interface User {
  id: string;
  email: string;
  role: "admin" | "user";
}

export interface LoginResponse {
  access_token: string;
  user: User;
}

export async function login(email: string): Promise<LoginResponse> {
  const res = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch {
    // best effort — ignore any failure (e.g. backend down, network error)
  }
}

export async function me(): Promise<User> {
  return apiFetch<User>("/auth/me");
}
