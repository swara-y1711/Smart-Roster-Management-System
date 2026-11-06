import { getSupabaseBrowserClient } from "@/lib/supabase/client";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function errorMessage(response: Response) {
  try {
    const body = await response.json();
    const detail = typeof body?.detail === "string"
      ? body.detail
      : typeof body?.detail?.message === "string"
        ? body.detail.message
        : body?.message;
    return { message: detail || `Request failed (${response.status}).`, body };
  } catch {
    return { message: `Request failed (${response.status}).`, body: undefined };
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const supabase = getSupabaseBrowserClient();
  const session = supabase ? (await supabase.auth.getSession()).data.session : null;
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers, cache: "no-store" });
  if (!response.ok) {
    const error = await errorMessage(response);
    throw new ApiError(response.status, error.message, error.body);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => apiRequest<T>(path),
  post: <T>(path: string, body: unknown) => apiRequest<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) => apiRequest<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) => apiRequest<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => apiRequest<T>(path, { method: "DELETE" }),
};

export function apiErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Please sign in again.";
    if (error.status === 403) return error.message || "You do not have permission to access this organization.";
    if (error.status === 404) return "The requested record was not found.";
    if (error.status === 422) return error.message || "Please check the submitted values.";
    return error.message;
  }
  return error instanceof Error ? error.message : "Unable to reach the RosterIQ API.";
}
