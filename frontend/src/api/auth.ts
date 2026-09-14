import { apiFetch } from "./client";
import type { LoginRequest, RegisterRequest, RegisterResponse, TokenResponse } from "./types";

export function login(payload: LoginRequest): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/auth/login", { method: "POST", body: payload, anonymous: true });
}

export function register(payload: RegisterRequest): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>("/api/auth/register", { method: "POST", body: payload, anonymous: true });
}
