export async function fetchFromAPI(endpoint: string, options: RequestInit = {}) {
  const candidateBases: string[] = [];
  const isBrowser = typeof window !== "undefined";
  const isLocalhost = isBrowser && (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname === "0.0.0.0"
  );

  // 1. Explicit public API URL configured via environment variable
  if (process.env.NEXT_PUBLIC_API_URL) {
    const pubUrl = process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
    candidateBases.push(pubUrl.endsWith("/api/v1") ? pubUrl : `${pubUrl}/api/v1`);
  }

  // 2. In browser: relative path proxies cleanly through Next.js / Vercel without CORS or mixed content
  if (isBrowser) {
    candidateBases.push("/api/v1");
  }

  // 3. In SSR / Node server-side runtime
  if (!isBrowser) {
    if (process.env.BACKEND_URL) {
      const bUrl = process.env.BACKEND_URL.replace(/\/+$/, "");
      candidateBases.push(bUrl.endsWith("/api/v1") ? bUrl : `${bUrl}/api/v1`);
    }
    if (process.env.VERCEL_URL) {
      candidateBases.push(`https://${process.env.VERCEL_URL}/api/v1`);
    }
  }

  // 4. Local development fallbacks ONLY for local development environments
  if (isLocalhost || (!isBrowser && process.env.NODE_ENV !== "production")) {
    candidateBases.push("http://127.0.0.1:8000/api/v1");
    candidateBases.push("http://localhost:8000/api/v1");
  }

  let lastError: any = null;

  for (const base of candidateBases) {
    try {
      const url = `${base}${endpoint}`;
      const res = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
        next: { revalidate: 0 }
      });

      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      lastError = err;
    }
  }

  // Surface errors visibly in console
  console.warn(
    `[CycloneX API] Failed to fetch endpoint "${endpoint}" across candidate bases: [${candidateBases.join(", ")}].`,
    lastError
  );
  return null;
}
