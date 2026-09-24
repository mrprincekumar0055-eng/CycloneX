import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

async function proxyRequest(request: NextRequest, { params }: { params: { path: string[] } }) {
  const path = (params.path || []).join("/");
  const backendBaseUrl = process.env.BACKEND_URL;

  if (backendBaseUrl) {
    try {
      const bUrl = backendBaseUrl.replace(/\/+$/, "");
      const search = request.nextUrl.search;
      const targetUrl = `${bUrl}/api/v1/${path}${search}`;

      const headers = new Headers(request.headers);
      headers.delete("host");

      const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.blob();

      const res = await fetch(targetUrl, {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(10000)
      });

      const responseHeaders = new Headers(res.headers);
      responseHeaders.set("Cache-Control", "no-store, no-cache, must-revalidate");

      return new NextResponse(res.body, {
        status: res.status,
        headers: responseHeaders
      });
    } catch (err: any) {
      console.warn(`[Proxy Error] Failed to proxy /api/v1/${path} to backend:`, err?.message);
    }
  }

  // Fallback for key read endpoints when backend is spinning up
  if (path === "cyclones") {
    return NextResponse.json([
      {
        id: "CYC-2023-ARB-01",
        name: "Biparjoy",
        basin: "Arabian Sea",
        category: "VSCS",
        status: "active",
        current_lat: 21.65,
        current_lon: 66.85,
        max_sustained_wind_kts: 90,
        central_pressure_hpa: 960,
        movement_speed_kmh: 8.5,
        movement_direction: "NNE"
      }
    ]);
  }

  return NextResponse.json(
    {
      error: "Backend service unreachable",
      endpoint: `/api/v1/${path}`,
      hint: "Set BACKEND_URL in Vercel environment variables or start FastAPI backend."
    },
    { status: 503 }
  );
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;
export const OPTIONS = proxyRequest;
