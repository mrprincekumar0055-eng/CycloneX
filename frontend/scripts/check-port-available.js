#!/usr/bin/env node
/**
 * CycloneX Pre-Build Port Conflict Guard
 * 
 * Verifies that port 3000 is NOT bound to an active process before running `next build`.
 * Running `next build` while `next dev` is running overwrites `.next` with production hashes,
 * causing the running dev server to serve broken HTML with missing/404 stylesheets.
 * 
 * Fails loudly with exit code 1 if port 3000 is occupied.
 */

const net = require("net");

const RED = "\x1b[91m";
const YELLOW = "\x1b[93m";
const GREEN = "\x1b[92m";
const CYAN = "\x1b[96m";
const BOLD = "\x1b[1m";
const RESET = "\x1b[0m";

if (process.env.ALLOW_PORT_IN_USE === "true" || process.env.SKIP_PORT_CHECK === "true") {
  console.log(`${YELLOW}[WARN] Port 3000 check skipped via environment override.${RESET}`);
  process.exit(0);
}

function checkPort(port, host) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(800);
    socket.on("connect", () => {
      socket.destroy();
      resolve(true); // Connected: Port is in use
    });
    socket.on("timeout", () => {
      socket.destroy();
      resolve(false);
    });
    socket.on("error", () => {
      resolve(false); // Refused: Port is free
    });
    socket.connect(port, host);
  });
}

async function main() {
  const port = parseInt(process.env.PORT || "3000", 10);
  const hosts = ["127.0.0.1", "::1", "localhost"];

  let portInUse = false;
  let detectedHost = "";

  for (const host of hosts) {
    const inUse = await checkPort(port, host);
    if (inUse) {
      portInUse = true;
      detectedHost = host;
      break;
    }
  }

  if (portInUse) {
    console.error(`\n${RED}${BOLD}==============================================================================${RESET}`);
    console.error(`${RED}${BOLD}  [FATAL ERROR] PORT ${port} IS ALREADY BOUND TO A RUNNING PROCESS!${RESET}`);
    console.error(`${RED}${BOLD}==============================================================================${RESET}`);
    console.error(`  An active server is currently running on ${detectedHost}:${port} (e.g. 'npm run dev' or 'next start').`);
    console.error("");
    console.error(`  ${YELLOW}${BOLD}WHY THIS BUILD IS BLOCKED:${RESET}`);
    console.error(`  Running 'next build' while a development server is active wipes the '.next'`);
    console.error(`  directory and clobbers in-memory CSS manifests, causing the active server to`);
    console.error(`  serve 404s on stylesheets and rendering all pages as unstyled raw HTML.`);
    console.error("");
    console.error(`  ${CYAN}${BOLD}RULE:${RESET} Never run 'npm run build' while 'npm run dev' is active on port ${port}.`);
    console.error("");
    console.error(`  ${GREEN}${BOLD}ACTION REQUIRED:${RESET}`);
    console.error(`  1. Terminate the process currently running on port ${port}.`);
    console.error(`     - In PowerShell/CMD: Run 'Stop-Process -Id (Get-NetTCPConnection -LocalPort ${port}).OwningProcess -Force'`);
    console.error(`     - Or stop the terminal tab running 'npm run dev'`);
    console.error(`  2. Re-run 'npm run build' once port ${port} is free.`);
    console.error(`${RED}${BOLD}==============================================================================${RESET}\n`);
    process.exit(1);
  } else {
    console.log(`${GREEN}[PASS] Port ${port} is clear. No conflicting dev server detected. Proceeding with build...${RESET}`);
    process.exit(0);
  }
}

main().catch((err) => {
  console.error(`[WARN] Could not verify port status: ${err.message}. Proceeding cautiously.`);
  process.exit(0);
});

