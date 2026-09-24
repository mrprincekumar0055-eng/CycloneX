import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const backendBaseUrl = process.env.BACKEND_URL;
  let backendHealth = "not_configured";

  if (backendBaseUrl) {
    try {
      const bRes = await fetch(`${backendBaseUrl.replace(/\/+$/, "")}/health`, {
        signal: AbortSignal.timeout(4000),
        cache: "no-store"
      });
      backendHealth = bRes.ok ? "connected" : `http_${bRes.status}`;
    } catch {
      backendHealth = "unreachable";
    }
  }

  return NextResponse.json({
    status: "ok",
    service: "cyclonex-api",
    backend_status: backendHealth,
    timestamp: new Date().toISOString()
  });
}
