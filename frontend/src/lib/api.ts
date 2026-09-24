export async function fetchFromAPI(endpoint: string, options: RequestInit = {}) {
  const candidateBases: string[] = [];

  if (process.env.NEXT_PUBLIC_API_URL) {
    candidateBases.push(process.env.NEXT_PUBLIC_API_URL);
  }

  // In browser, relative path proxies cleanly through Next.js rewrites without CORS/host mismatch
  if (typeof window !== "undefined") {
    candidateBases.push("/api/v1");
  }

  // Direct backend endpoints (IPv4 and localhost)
  candidateBases.push("http://127.0.0.1:8000/api/v1");
  candidateBases.push("http://localhost:8000/api/v1");

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

  // Surface errors visibly in browser DevTools console
  console.error(
    `[CycloneX API Error] Failed to fetch endpoint "${endpoint}" across all candidate bases: [${candidateBases.join(", ")}]. Check backend server status on port 8000.`,
    lastError
  );
  return null;
}
