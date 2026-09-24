/**
 * CycloneX Centralized API Client
 * Single source of truth for all frontend-to-backend communication.
 * 
 * Production Configuration:
 * - Set NEXT_PUBLIC_API_BASE_URL in Vercel to your public FastAPI domain (e.g. https://cyclonex-api.onrender.com).
 * - Or set BACKEND_URL for server-side Next.js rewrites proxying /api/v1/:path*.
 * - Never calls localhost or 127.0.0.1 in a production browser.
 */

export function getApiBaseUrl(): string {
  // 1. Explicit public backend URL configured via environment variable
  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim() !== "") {
    const clean = envUrl.trim().replace(/\/+$/, "");
    return clean.endsWith("/api/v1") ? clean : `${clean}/api/v1`;
  }

  const isBrowser = typeof window !== "undefined";
  const isLocalhost = isBrowser && (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname === "0.0.0.0"
  );

  // 2. Server-side runtime with BACKEND_URL
  if (!isBrowser && process.env.BACKEND_URL) {
    const clean = process.env.BACKEND_URL.trim().replace(/\/+$/, "");
    return clean.endsWith("/api/v1") ? clean : `${clean}/api/v1`;
  }

  // 3. Localhost development environment
  if (isLocalhost || (!isBrowser && process.env.NODE_ENV !== "production")) {
    return "http://127.0.0.1:8000/api/v1";
  }

  // 4. Production browser: use relative /api/v1 (proxied through Next.js rewrite)
  return "/api/v1";
}

export function isBackendConfigured(): boolean {
  if (typeof window !== "undefined") {
    const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocalhost) return true;
  }
  return Boolean(process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL);
}

export async function fetchFromAPI(endpoint: string, options: RequestInit = {}): Promise<any> {
  const base = getApiBaseUrl();
  const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${base}${normalizedEndpoint}`;

  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        ...options.headers,
      },
      next: { revalidate: 0 }
    });

    if (res.ok) {
      return await res.json();
    }

    // Backend returned non-2xx HTTP status (e.g. 404, 500, 502, 503)
    console.warn(`[CycloneX API] HTTP ${res.status} for ${endpoint} on ${base}`);
    return null;
  } catch (err: any) {
    // Network failure (connection refused, DNS failure, offline backend)
    console.warn(`[CycloneX API Network Error] Failed to reach backend at ${url}:`, err?.message || err);
    return null;
  }
}
