#!/usr/bin/env node
"use strict";

// src/skills/login.ts
var import_node_fs3 = require("node:fs");
var import_node_path3 = require("node:path");
var import_node_os3 = require("node:os");

// src/config.ts
var import_node_fs2 = require("node:fs");
var import_node_path2 = require("node:path");
var import_node_os2 = require("node:os");

// src/services/auth.ts
var import_node_http = require("node:http");
var import_node_fs = require("node:fs");
var import_node_path = require("node:path");
var import_node_os = require("node:os");
var import_node_crypto = require("node:crypto");

// src/services/openUrl.ts
var import_node_child_process = require("node:child_process");
function run(command, args) {
  return new Promise((resolve, reject) => {
    (0, import_node_child_process.execFile)(command, args, { windowsHide: true }, (error) => {
      if (error) reject(error);
      else resolve();
    });
  });
}
async function openUrl(url) {
  const href = url.toString();
  if (!/^https?:\/\//i.test(href)) {
    throw new Error("Refusing to open non-http URL");
  }
  if (process.platform === "win32") {
    try {
      await run("rundll32.exe", ["url.dll,FileProtocolHandler", href]);
      return;
    } catch {
    }
    await run("cmd.exe", ["/c", "start", '""', href]);
    return;
  }
  if (process.platform === "darwin") {
    await run("open", [href]);
    return;
  }
  await run("xdg-open", [href]);
}

// src/services/auth.ts
var SUPERMEMORY_DIR = (0, import_node_path.join)((0, import_node_os.homedir)(), ".codex", "supermemory");
var CREDENTIALS_FILE = (0, import_node_path.join)(SUPERMEMORY_DIR, "credentials.json");
var AUTH_BASE_URL = process.env.SUPERMEMORY_AUTH_URL || "https://app.supermemory.ai/auth/agent-connect";
var AUTH_TIMEOUT = Number(process.env.SUPERMEMORY_AUTH_TIMEOUT) || 5 * 6e4;
var AUTH_SUCCESS_HTML = `<!DOCTYPE html>
<html><head><title>Connected - Supermemory</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:100vh;background:#faf9f6}
.dot{width:10px;height:10px;background:#22c55e;border-radius:50%;display:inline-block;margin-right:8px}
h1{font-size:32px;font-weight:500;color:#1a1a1a;margin:16px 0}
p{color:#666;font-size:16px}
</style></head><body>
<div><span class="dot"></span><span style="color:#22c55e;font-size:14px">Connected</span></div>
<h1>Supermemory is ready</h1>
<p>You can close this tab and return to Codex.</p>
</body></html>`;
var AUTH_ERROR_HTML = `<!DOCTYPE html>
<html><head><title>Error - Supermemory</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:100vh;background:#faf9f6}
.dot{width:10px;height:10px;background:#ef4444;border-radius:50%;display:inline-block;margin-right:8px}
h1{font-size:32px;font-weight:500;color:#1a1a1a;margin:16px 0}
p{color:#666;font-size:16px}
</style></head><body>
<div><span class="dot"></span><span style="color:#ef4444;font-size:14px">Error</span></div>
<h1>Connection Failed</h1>
<p>Invalid API key received. Please try again.</p>
</body></html>`;
function loadCredentialData() {
  try {
    if ((0, import_node_fs.existsSync)(CREDENTIALS_FILE)) {
      return JSON.parse((0, import_node_fs.readFileSync)(CREDENTIALS_FILE, "utf-8"));
    }
  } catch {
  }
  return null;
}
function loadCredentials() {
  const data = loadCredentialData();
  if (data?.apiKey) return data.apiKey;
  return void 0;
}
function normalizeApiBaseUrl(apiBaseUrl) {
  if (!apiBaseUrl) return void 0;
  try {
    const url = new URL(apiBaseUrl);
    if (url.protocol !== "https:" && url.protocol !== "http:") return void 0;
    url.pathname = url.pathname.replace(/\/+$/, "");
    url.search = "";
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return void 0;
  }
}
function saveCredentials(apiKey, apiBaseUrl) {
  (0, import_node_fs.mkdirSync)(SUPERMEMORY_DIR, { recursive: true, mode: 448 });
  const credentials = { apiKey, savedAt: (/* @__PURE__ */ new Date()).toISOString() };
  const normalizedApiBaseUrl = normalizeApiBaseUrl(apiBaseUrl);
  if (normalizedApiBaseUrl) credentials.apiBaseUrl = normalizedApiBaseUrl;
  (0, import_node_fs.writeFileSync)(
    CREDENTIALS_FILE,
    JSON.stringify(credentials, null, 2),
    { mode: 384 }
  );
}
function startAuthFlow() {
  return new Promise((resolve, reject) => {
    let resolved = false;
    const stateToken = (0, import_node_crypto.randomBytes)(16).toString("hex");
    const server = (0, import_node_http.createServer)((req, res) => {
      const url = new URL(req.url || "/", "http://localhost");
      if (url.pathname === "/callback") {
        const callbackState = url.searchParams.get("state");
        if (callbackState !== stateToken) {
          res.writeHead(403, { "Content-Type": "text/html" });
          res.end(AUTH_ERROR_HTML);
          return;
        }
        const apiKey = url.searchParams.get("apikey") || url.searchParams.get("api_key");
        const apiBaseUrl = url.searchParams.get("api_url") || url.searchParams.get("api_base_url");
        if (apiKey?.startsWith("sm_")) {
          saveCredentials(apiKey, apiBaseUrl ?? void 0);
          res.writeHead(200, { "Content-Type": "text/html" });
          res.end(AUTH_SUCCESS_HTML);
          resolved = true;
          clearTimeout(timer);
          server.close();
          resolve(apiKey);
        } else {
          res.writeHead(400, { "Content-Type": "text/html" });
          res.end(AUTH_ERROR_HTML);
        }
      } else {
        res.writeHead(404);
        res.end("Not found");
      }
    });
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      const callbackUrl = `http://127.0.0.1:${port}/callback?state=${stateToken}`;
      const params = new URLSearchParams({
        callback: callbackUrl,
        client: "codex",
        hostname: `codex - ${(0, import_node_os.hostname)()}`,
        os: `${(0, import_node_os.platform)()}-${(0, import_node_os.arch)()}`,
        cwd: process.cwd(),
        cli_version: "1.0.0"
      });
      const authUrl = `${AUTH_BASE_URL}?${params.toString()}`;
      openUrl(authUrl).catch((error) => {
        if (!resolved) {
          clearTimeout(timer);
          server.close();
          reject(new Error(`Failed to open browser: ${error.message}`));
        }
      });
    });
    server.on("error", (err) => {
      if (!resolved) {
        clearTimeout(timer);
        reject(new Error(`Failed to start auth server: ${err.message}`));
      }
    });
    const timer = setTimeout(() => {
      if (!resolved) {
        server.close();
        reject(new Error("AUTH_TIMEOUT"));
      }
    }, AUTH_TIMEOUT);
  });
}

// src/config.ts
var CONFIG_FILE = (0, import_node_path2.join)((0, import_node_os2.homedir)(), ".codex", "supermemory.json");
var DEFAULT_SIGNAL_KEYWORDS = [
  "prefer",
  "like",
  "love",
  "use",
  "hate",
  "dislike",
  "avoid",
  "remember",
  "forget",
  "note",
  "decision",
  "decided",
  "chose",
  "choose",
  "picked",
  "switched",
  "moved",
  "migrated",
  "architecture",
  "pattern",
  "approach",
  "design",
  "tradeoff",
  "implementation",
  "refactor",
  "upgrade",
  "deprecate",
  "bug",
  "fix",
  "fixed",
  "solved",
  "solution",
  "important",
  "stack",
  "framework",
  "library",
  "tool",
  "database"
];
var DEFAULTS = {
  similarityThreshold: 0.6,
  maxMemories: 5,
  maxProfileItems: 5,
  injectProfile: true,
  containerTagPrefix: "codex",
  filterPrompt: "You are a stateful coding agent. Remember all the information, including but not limited to user's coding preferences, tech stack, behaviours, workflows, and any other relevant details.",
  debug: false,
  signalExtraction: false,
  signalKeywords: DEFAULT_SIGNAL_KEYWORDS,
  signalTurnsBefore: 3,
  autoSaveEveryTurns: 3,
  autoRecallEveryPrompt: false,
  captureEveryNTurns: 0
};
function loadRawConfig() {
  if ((0, import_node_fs2.existsSync)(CONFIG_FILE)) {
    try {
      const content = (0, import_node_fs2.readFileSync)(CONFIG_FILE, "utf-8");
      return { config: JSON.parse(content), existed: true };
    } catch {
      return { config: {}, existed: true };
    }
  }
  return { config: {}, existed: false };
}
var { config: fileConfig, existed: configExisted } = loadRawConfig();
function resolveCaptureEveryNTurns(config) {
  if (config.captureEveryNTurns !== void 0) return config.captureEveryNTurns;
  if (config.autoSaveEveryTurns !== void 0) return config.autoSaveEveryTurns;
  if (configExisted) return 3;
  return DEFAULTS.captureEveryNTurns;
}
function resolveAutoRecallEveryPrompt(config) {
  if (config.autoRecallEveryPrompt !== void 0) return config.autoRecallEveryPrompt;
  if (configExisted) return true;
  return DEFAULTS.autoRecallEveryPrompt;
}
function getApiKey() {
  if (process.env.SUPERMEMORY_CODEX_API_KEY) return process.env.SUPERMEMORY_CODEX_API_KEY;
  if (fileConfig.apiKey) return fileConfig.apiKey;
  return loadCredentials();
}
var SUPERMEMORY_API_KEY = getApiKey();
var CONFIG = {
  similarityThreshold: fileConfig.similarityThreshold ?? DEFAULTS.similarityThreshold,
  maxMemories: fileConfig.maxMemories ?? DEFAULTS.maxMemories,
  maxProfileItems: fileConfig.maxProfileItems ?? DEFAULTS.maxProfileItems,
  injectProfile: fileConfig.injectProfile ?? DEFAULTS.injectProfile,
  containerTagPrefix: fileConfig.containerTagPrefix ?? DEFAULTS.containerTagPrefix,
  userContainerTag: fileConfig.userContainerTag,
  projectContainerTag: fileConfig.projectContainerTag,
  filterPrompt: fileConfig.filterPrompt ?? DEFAULTS.filterPrompt,
  debug: fileConfig.debug ?? DEFAULTS.debug,
  signalExtraction: fileConfig.signalExtraction ?? DEFAULTS.signalExtraction,
  signalKeywords: fileConfig.signalKeywords ?? DEFAULTS.signalKeywords,
  signalTurnsBefore: fileConfig.signalTurnsBefore ?? DEFAULTS.signalTurnsBefore,
  autoSaveEveryTurns: fileConfig.autoSaveEveryTurns ?? DEFAULTS.autoSaveEveryTurns,
  autoRecallEveryPrompt: resolveAutoRecallEveryPrompt(fileConfig),
  captureEveryNTurns: resolveCaptureEveryNTurns(fileConfig),
  enableCustomContainers: fileConfig.enableCustomContainers ?? false,
  customContainers: (fileConfig.customContainers ?? []).filter(
    (c) => !!c && typeof c.tag === "string" && typeof c.description === "string"
  ),
  customContainerInstructions: fileConfig.customContainerInstructions ?? ""
};
function isConfigured() {
  return !!SUPERMEMORY_API_KEY;
}

// src/skills/login.ts
var AUTH_ATTEMPTED_FILE = (0, import_node_path3.join)((0, import_node_os3.homedir)(), ".codex", "supermemory", ".auth-attempted");
var LOGGED_OUT_FILE = (0, import_node_path3.join)((0, import_node_os3.homedir)(), ".codex", "supermemory", ".logged-out");
async function main() {
  try {
    if ((0, import_node_fs3.existsSync)(LOGGED_OUT_FILE)) (0, import_node_fs3.unlinkSync)(LOGGED_OUT_FILE);
  } catch {
  }
  if (isConfigured()) {
    console.log("Already authenticated with Supermemory. Memory is active.");
    console.log(`To re-authenticate, remove ${CREDENTIALS_FILE} and run this again.`);
    process.exit(0);
  }
  try {
    if ((0, import_node_fs3.existsSync)(AUTH_ATTEMPTED_FILE)) (0, import_node_fs3.unlinkSync)(AUTH_ATTEMPTED_FILE);
  } catch {
  }
  console.log("Opening browser to authenticate with Supermemory...");
  console.log(`If the browser does not open, visit: ${AUTH_BASE_URL}`);
  try {
    await startAuthFlow();
    try {
      if ((0, import_node_fs3.existsSync)(AUTH_ATTEMPTED_FILE)) (0, import_node_fs3.unlinkSync)(AUTH_ATTEMPTED_FILE);
    } catch {
    }
    console.log("\nAuthenticated successfully! Supermemory is now active.");
    process.exit(0);
  } catch (err) {
    const isTimeout = err instanceof Error && err.message === "AUTH_TIMEOUT";
    if (isTimeout) {
      console.error("\nAuthentication timed out. Please try again.");
    } else {
      console.error("\nAuthentication failed:", err instanceof Error ? err.message : err);
    }
    console.error(`
Alternatively, set the API key manually:`);
    console.error(`  export SUPERMEMORY_CODEX_API_KEY="sm_..."`);
    console.error(`  Get your key at: https://app.supermemory.ai/?view=integrations`);
    process.exit(1);
  }
}
main().catch((err) => {
  console.error("Fatal:", err instanceof Error ? err.message : err);
  process.exit(1);
});
