/**
 * Typed API client.
 *
 * One place that knows about tokens, error shapes and the base URL. Errors are
 * surfaced as `ApiError` with the server's message intact — an accountant
 * seeing "Xatolik" with no explanation will call support, and support calls at
 * $75/month are the difference between a viable business and a hobby.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_PREFIX = "/api/v1";

const ACCESS_TOKEN_KEY = "hujjatai.access_token";
const REFRESH_TOKEN_KEY = "hujjatai.refresh_token";

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function parseError(response: Response): Promise<never> {
  let message = `${response.status} ${response.statusText}`;
  let details: unknown;
  try {
    const body = await response.json();
    details = body;
    if (typeof body.detail === "string") {
      message = body.detail;
    } else if (Array.isArray(body.errors) && body.errors.length > 0) {
      message = body.errors.map((e: { field: string; message: string }) =>
        `${e.field}: ${e.message}`).join("; ");
    } else if (body.detail?.message) {
      message = body.detail.message;
    }
  } catch {
    // Non-JSON error body: keep the status line.
  }
  throw new ApiError(message, response.status, details);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${API_PREFIX}${path}`, { ...init, headers });

  if (response.status === 401 && typeof window !== "undefined") {
    clearTokens();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
  if (!response.ok) await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// --- Types -------------------------------------------------------------------

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  company_id: number;
  is_active: boolean;
}

export interface Company {
  id: number;
  name: string;
  tin: string | null;
  address: string | null;
  locale: string;
  plan: string;
  monthly_document_quota: number;
  onec_config: Record<string, unknown>;
}

export interface DocumentSummary {
  id: number;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  page_count: number | null;
  status: string;
  doc_type: string;
  error_message: string | null;
  processing_ms: number | null;
  created_at: string;
}

export interface ExtractedField {
  value: string | number | null;
  confidence: number;
  source: string;
  raw_text: string | null;
  page: number | null;
  bbox: number[] | null;
}

export interface LineItem {
  index: number;
  description: string | null;
  unit: string | null;
  quantity: string | null;
  unit_price: string | null;
  amount: string | null;
  confidence: number;
  raw_text: string | null;
}

export interface ValidationIssue {
  code: string;
  message: string;
  fields: string[];
}

export interface Extraction {
  id: number;
  document_id: number;
  version: number;
  strategy: string;
  model_name: string | null;
  fields: Record<string, ExtractedField>;
  line_items: LineItem[];
  validation: {
    errors?: ValidationIssue[];
    warnings?: ValidationIssue[];
    checks?: Record<string, boolean>;
    registry_repairs?: Array<{ field: string; from: string | null; to: string | null; reason: string }>;
    is_valid?: boolean;
  };
  overall_confidence: number;
  total_amount: string | null;
  currency: string | null;
  is_accepted: boolean;
  created_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  extraction: Extraction | null;
  script_summary: Record<string, unknown> | null;
  ocr_provider: string | null;
}

export interface DocumentList {
  items: DocumentSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadResult {
  accepted: DocumentSummary[];
  rejected: { filename: string; reason: string }[];
}

export interface DashboardStats {
  documents_this_month: number;
  documents_total: number;
  confirmed_this_month: number;
  needs_review: number;
  failed_this_month: number;
  average_confidence: number;
  average_processing_ms: number | null;
  minutes_saved_this_month: number;
  api_cost_usd_this_month: number;
  quota: number;
  quota_used_percent: number;
  known_vendors: number;
  top_vendors: { vendor_tin: string; vendor_name: string; documents: number; template_active: boolean }[];
  corrections_this_month: number;
  correction_rate: number;
}

export interface ExportPreview {
  xml: string;
  document_count: number;
  problems: string[];
  total_amount: string | null;
}

// --- Endpoints ---------------------------------------------------------------

export const api = {
  register: (payload: {
    email: string; password: string; full_name?: string;
    company_name: string; company_tin?: string;
  }) => request<AuthTokens>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),

  login: (payload: { email: string; password: string }) =>
    request<AuthTokens>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),

  me: () => request<User>("/auth/me"),
  company: () => request<Company>("/auth/company"),
  updateCompany: (payload: Partial<Company>) =>
    request<Company>("/auth/company", { method: "PATCH", body: JSON.stringify(payload) }),
  users: () => request<User[]>("/auth/users"),
  inviteUser: (payload: { email: string; password: string; full_name?: string; role: string }) =>
    request<User>("/auth/users", { method: "POST", body: JSON.stringify(payload) }),

  upload: (files: File[]) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request<UploadResult>("/documents/upload", { method: "POST", body: form });
  },

  documents: (params: { status?: string; search?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.set("status", params.status);
    if (params.search) query.set("search", params.search);
    query.set("limit", String(params.limit ?? 50));
    query.set("offset", String(params.offset ?? 0));
    return request<DocumentList>(`/documents?${query.toString()}`);
  },

  document: (id: number) => request<DocumentDetail>(`/documents/${id}`),
  documentText: (id: number) =>
    request<{ provider: string; text: string; script_summary: Record<string, unknown> }>(
      `/documents/${id}/text`),
  reviewDocument: (id: number, payload: {
    fields: Record<string, unknown>; line_items?: LineItem[]; accept: boolean;
  }) => request<Extraction>(`/documents/${id}/review`, {
    method: "POST", body: JSON.stringify(payload),
  }),
  reprocessDocument: (id: number) =>
    request<DocumentSummary>(`/documents/${id}/reprocess`, { method: "POST" }),
  deleteDocument: (id: number) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  dashboard: () => request<DashboardStats>("/dashboard"),

  exportPreview: (documentIds: number[]) =>
    request<ExportPreview>("/exports/preview", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds, format: "commerceml_208" }),
    }),

  /** Downloads the 1C file. Uses fetch directly so the blob keeps its filename. */
  downloadExport: async (documentIds: number[]): Promise<void> => {
    const token = getAccessToken();
    const response = await fetch(`${API_URL}${API_PREFIX}/exports/commerceml`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ document_ids: documentIds, format: "commerceml_208" }),
    });
    if (!response.ok) await parseError(response);

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = match?.[1] ?? "hujjatai-1c.xml";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  /** Fetches the original scan as an object URL for the review pane. */
  documentFileUrl: async (id: number): Promise<string> => {
    const token = getAccessToken();
    const response = await fetch(`${API_URL}${API_PREFIX}/documents/${id}/file`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) await parseError(response);
    return window.URL.createObjectURL(await response.blob());
  },
};
