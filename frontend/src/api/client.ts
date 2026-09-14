import { authStorage } from "@/lib/authStorage";
import type { ErrorEnvelope } from "./types";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";

/**
 * Every backend error is `{"error": {"code","message","field_errors"}}`
 * (frozen contract, DESIGN.md §6, verified live in openapi.json's
 * exception handlers). This is the one place that shape is unwrapped so no
 * feature code has to know the envelope exists.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: Record<string, string> | null;

  constructor(status: number, code: string, message: string, fieldErrors: Record<string, string> | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors;
  }

  /** True when the backend never answered at all (offline, DNS, CORS-block). */
  static isNetworkFailure(err: unknown): err is ApiError {
    return err instanceof ApiError && err.code === "network_error";
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE" | "PUT";
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
  /** Skip attaching the bearer token (login/register only). */
  anonymous?: boolean;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path, API_BASE_URL);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, query, signal, anonymous } = options;

  const headers: Record<string, string> = {};
  if (!anonymous) {
    const token = authStorage.get();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  if (body !== undefined && !formData) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal,
    });
  } catch {
    throw new ApiError(0, "network_error", "Could not reach the server. Check your connection and try again.", null);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    if (response.status === 401 && !anonymous) {
      authStorage.clear();
    }
    const envelope = data as ErrorEnvelope | null;
    if (envelope?.error) {
      throw new ApiError(response.status, envelope.error.code, envelope.error.message, envelope.error.field_errors);
    }
    throw new ApiError(response.status, "unknown_error", "Something went wrong. Please try again.", null);
  }

  return data as T;
}
