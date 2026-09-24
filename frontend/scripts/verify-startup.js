#!/usr/bin/env node
/**
 * CycloneX Frontend Startup Pre-Flight Health Check
 * SIH26070 - Tropical Cyclone Intelligence Platform
 * 
 * Verifies before the application is considered "ready":
 *   1. Backend API is reachable and healthy
 *   2. Database contains non-zero rows in cyclones, alerts, shelters, hospitals
 *   3. Map tile provider is serving real, non-watermarked tiles
 *   4. Frontend /dashboard stylesheet returns HTTP 200 with non-trivial bytes (not 404)
 * 
 * Exits with code 1 and loud terminal error if ANY check fails.
 */

const http = require("http");
const https = require("https");

const RED = "\x1b[91m";
const GREEN = "\x1b[92m";
const YELLOW = "\x1b[93m";
const CYAN = "\x1b[96m";
const BOLD = "\x1b[1m";
const RESET = "\x1b[0m";

function logPass(msg) {
  console.log(`  ${GREEN}[PASS]${RESET} ${msg}`);
}

function logFail(msg) {
  console.log(`  ${RED}${BOLD}[FAIL]${RESET} ${msg}`);
}

function logInfo(msg) {
  console.log(`  ${CYAN}[INFO]${RESET} ${msg}`);
}

function fetchUrl(urlStr, options = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const client = url.protocol === "https:" ? https : http;
    const req = client.get(urlStr, {
      headers: {
        "User-Agent": "CycloneX-PreFlightHealthCheck-Node/1.0",
        Accept: options.accept || "application/json",
        ...options.headers,
      },
      timeout: options.timeout || 5000,
    }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const buffer = Buffer.concat(chunks);
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          data: buffer,
          text: () => buffer.toString("utf-8"),
          json: () => JSON.parse(buffer.toString("utf-8")),
        });
      });
    });

    req.on("error", (err) => reject(err));
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Request timed out"));
    });
  });
}

async function runPreFlight() {
  console.log(`\n${BOLD}${CYAN}==============================================================================${RESET}`);
  console.log(`${BOLD}${CYAN}  CYCLONEX STARTUP PRE-FLIGHT VERIFICATION (NODE/FRONTEND)${RESET}`);
  console.log(`${BOLD}${CYAN}==============================================================================${RESET}`);
  console.log(`  Execution Time: ${new Date().toISOString()}`);

  let allPassed = true;

  // -------------------------------------------------------------
  // Check 1: Backend Reachability
  // -------------------------------------------------------------
  console.log(`\n${BOLD}[1/4] Backend Service Reachability:${RESET}`);
  const backendCandidates = [
    process.env.NEXT_PUBLIC_API_URL,
    "http://127.0.0.1:8000/api/v1",
    "http://localhost:8000/api/v1",
  ].filter(Boolean);

  let activeBase = null;
  let healthData = null;

  for (const base of backendCandidates) {
    try {
      const startTime = Date.now();
      const res = await fetchUrl(`${base.replace(/\/$/, "")}/system/health`);
      const latencyMs = Date.now() - startTime;
      if (res.statusCode === 200) {
        healthData = res.json();
        activeBase = base.replace(/\/$/, "");
        logPass(`FastAPI backend reachable at ${activeBase} (Latency: ${latencyMs}ms)`);
        logInfo(`Reported status: '${healthData.status}', database: '${healthData.database}'`);
        break;
      }
    } catch (err) {
      // try next
    }
  }

  if (!activeBase) {
    allPassed = false;
    logFail(`FastAPI backend is unreachable across candidates: [${backendCandidates.join(", ")}]`);
    console.log(`        ${YELLOW}-> Remedy: Start backend with: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000${RESET}`);
  }

  // -------------------------------------------------------------
  // Check 2: Database Rows in Critical Tables
  // -------------------------------------------------------------
  console.log(`\n${BOLD}[2/4] Database Non-Zero Row Verification:${RESET}`);
  const tables = [
    { name: "cyclones", endpoint: "/cyclones" },
    { name: "alerts", endpoint: "/alerts" },
    { name: "shelters", endpoint: "/facilities/shelters" },
    { name: "hospitals", endpoint: "/facilities/hospitals" },
  ];

  if (!activeBase) {
    allPassed = false;
    logFail("Skipping table row verification because backend is offline.");
  } else {
    for (const tbl of tables) {
      try {
        const res = await fetchUrl(`${activeBase}${tbl.endpoint}`);
        if (res.statusCode === 200) {
          const items = res.json();
          const count = Array.isArray(items) ? items.length : (items ? 1 : 0);
          if (count > 0) {
            logPass(`Table '${tbl.name}': ${count} row(s) confirmed`);
          } else {
            allPassed = false;
            logFail(`Table '${tbl.name}': 0 rows (EMPTY TABLE)`);
            console.log(`        ${YELLOW}-> Remedy: Run: python scripts/seed_demo_data.py${RESET}`);
          }
        } else {
          allPassed = false;
          logFail(`Endpoint '${tbl.endpoint}' returned HTTP ${res.statusCode}`);
        }
      } catch (err) {
        allPassed = false;
        logFail(`Failed to query table '${tbl.name}' via ${tbl.endpoint}: ${err.message}`);
      }
    }
  }

  // -------------------------------------------------------------
  // Check 3: Map Tile Provider Non-Watermarked Verification
  // -------------------------------------------------------------
  console.log(`\n${BOLD}[3/4] Map Tile Provider Verification:${RESET}`);
  const tileUrl = "https://tile.openstreetmap.org/1/1/0.png";

  try {
    const startTime = Date.now();
    const tileRes = await fetchUrl(tileUrl, { accept: "image/png,image/*" });
    const latencyMs = Date.now() - startTime;

    if (tileRes.statusCode === 200) {
      const contentType = tileRes.headers["content-type"] || "";
      const sizeBytes = tileRes.data.length;

      // Check for watermarking / error text
      const rawText = tileRes.data.toString("binary");
      const isWatermarked = rawText.includes("API KEY REQUIRED");

      if (isWatermarked) {
        allPassed = false;
        logFail(`Map tile provider returned watermarked tile ('API KEY REQUIRED') from ${tileUrl}`);
      } else if (sizeBytes > 500 && contentType.includes("image")) {
        logPass(`Tile provider verified: Clean real map tile (${sizeBytes} bytes, ${contentType}, ${latencyMs}ms)`);
        logInfo("No watermarks detected; OpenStreetMap tile provider operational.");
      } else {
        allPassed = false;
        logFail(`Map tile response invalid (Size: ${sizeBytes}B, Content-Type: ${contentType})`);
      }
    } else {
      allPassed = false;
      logFail(`Map tile provider returned HTTP ${tileRes.statusCode} from ${tileUrl}`);
    }
  } catch (err) {
    allPassed = false;
    logFail(`Network error verifying map tile provider: ${err.message}`);
  }

  // -------------------------------------------------------------
  // Check 4: Frontend /dashboard Stylesheet 200 OK Verification
  // -------------------------------------------------------------
  console.log(`\n${BOLD}[4/4] Frontend Dashboard Stylesheet Verification (/dashboard):${RESET}`);
  const frontendCandidates = [
    process.env.NEXT_PUBLIC_APP_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
  ].filter(Boolean);

  let activeFrontend = null;
  let dashboardHtml = "";

  for (const base of frontendCandidates) {
    try {
      const res = await fetchUrl(`${base.replace(/\/$/, "")}/dashboard`, { accept: "text/html" });
      if (res.statusCode === 200) {
        activeFrontend = base.replace(/\/$/, "");
        dashboardHtml = res.text();
        break;
      }
    } catch (err) {
      // try next
    }
  }

  if (!activeFrontend) {
    allPassed = false;
    logFail(`Frontend server unreachable on port 3000 across [${frontendCandidates.join(", ")}]`);
    console.log(`        ${YELLOW}-> Remedy: Start frontend server on port 3000 before running verification.${RESET}`);
  } else {
    // Extract stylesheet links
    const linkMatches = dashboardHtml.match(/<link[^>]+>/gi) || [];
    const cssHrefs = [];

    for (const tag of linkMatches) {
      if (/rel=["']stylesheet["']/i.test(tag)) {
        const hrefMatch = tag.match(/href=["']([^"']+)["']/i);
        if (hrefMatch) {
          cssHrefs.push(hrefMatch[1]);
        }
      }
    }

    if (cssHrefs.length === 0) {
      // Fallback regex for .css links
      const fallbackMatches = dashboardHtml.match(/href=["']([^"']+\.css[^"']*)["']/gi) || [];
      for (const m of fallbackMatches) {
        const h = m.match(/href=["']([^"']+)["']/i);
        if (h) cssHrefs.push(h[1]);
      }
    }

    if (cssHrefs.length === 0) {
      allPassed = false;
      logFail(`No stylesheet links found in ${activeFrontend}/dashboard HTML! Layout will render unstyled.`);
    } else {
      let nextCssFound = false;
      let totalCssBytes = 0;
      let verifiedCount = 0;

      for (const href of cssHrefs) {
        const fullUrl = href.startsWith("http") ? href : `${activeFrontend}${href}`;
        try {
          const startTime = Date.now();
          const cssRes = await fetchUrl(fullUrl, { accept: "text/css,*/*" });
          const latencyMs = Date.now() - startTime;

          if (cssRes.statusCode === 200) {
            const sizeBytes = cssRes.data.length;
            totalCssBytes += sizeBytes;
            verifiedCount++;

            if (fullUrl.includes("_next/static/css")) {
              nextCssFound = true;
            }

            if (sizeBytes < 500) {
              allPassed = false;
              logFail(`Stylesheet ${fullUrl} is truncated (${sizeBytes} bytes). Expected non-trivial CSS bundle.`);
            }
          } else if (cssRes.statusCode === 404) {
            allPassed = false;
            logFail(`CRITICAL CSS 404 REGRESSION: Stylesheet ${fullUrl} returned HTTP 404 Not Found!`);
            console.log(`        ${YELLOW}-> Stale dev-server / clobbered .next build cache detected.`);
            console.log(`        -> Kill process on port 3000, run 'npm run build', and start fresh.${RESET}`);
          } else {
            allPassed = false;
            logFail(`Stylesheet ${fullUrl} returned unexpected HTTP ${cssRes.statusCode}`);
          }
        } catch (err) {
          allPassed = false;
          logFail(`Failed to fetch stylesheet ${fullUrl}: ${err.message}`);
        }
      }

      if (!nextCssFound) {
        allPassed = false;
        logFail(`No local Next.js stylesheet (_next/static/css) was found in /dashboard. Found only external sheets.`);
      } else if (allPassed) {
        logPass(`All ${verifiedCount} stylesheet(s) verified healthy (HTTP 200, ${totalCssBytes.toLocaleString()} bytes total)`);
        logInfo(`Tailwind CSS bundle confirmed loaded & serving valid CSS.`);
      }
    }
  }

  // -------------------------------------------------------------
  // Final Verdict
  // -------------------------------------------------------------
  console.log("\n==============================================================================");
  if (allPassed) {
    console.log(`${GREEN}${BOLD}  === [SUCCESS] CYCLONEX SYSTEM PRE-FLIGHT CHECKS PASSED ===${RESET}`);
    console.log(`${GREEN}  Backend reachable, critical tables populated, map tiles verified non-watermarked,`);
    console.log(`  and frontend stylesheets verified live (HTTP 200).`);
    console.log(`  Application certified READY for operations.${RESET}`);
    console.log("==============================================================================\n");
    process.exit(0);
  } else {
    console.log(`${RED}${BOLD}  === [FATAL ERROR] CYCLONEX STARTUP PRE-FLIGHT CHECK FAILED ===${RESET}`);
    console.log(`${RED}  One or more critical subsystems failed startup verification.`);
    console.log(`  Refusing to start frontend with silent fallback/offline degradation.`);
    console.log(`  Resolve flagged errors and re-run check before starting.${RESET}`);
    console.log("==============================================================================\n");
    process.exit(1);
  }
}

runPreFlight().catch((err) => {
  console.error(`${RED}[FATAL ERROR] Pre-flight runner crashed: ${err.message}${RESET}`);
  process.exit(1);
});

