#!/usr/bin/env node
"use strict";

// src/skills/logout.ts
var import_node_fs = require("node:fs");
var import_node_path2 = require("node:path");
var import_node_os2 = require("node:os");

// src/services/auth.ts
var import_node_path = require("node:path");
var import_node_os = require("node:os");
var SUPERMEMORY_DIR = (0, import_node_path.join)((0, import_node_os.homedir)(), ".codex", "supermemory");
var CREDENTIALS_FILE = (0, import_node_path.join)(SUPERMEMORY_DIR, "credentials.json");
var AUTH_BASE_URL = process.env.SUPERMEMORY_AUTH_URL || "https://app.supermemory.ai/auth/agent-connect";
var AUTH_TIMEOUT = Number(process.env.SUPERMEMORY_AUTH_TIMEOUT) || 5 * 6e4;

// src/skills/logout.ts
var SUPERMEMORY_DIR2 = (0, import_node_path2.join)((0, import_node_os2.homedir)(), ".codex", "supermemory");
var AUTH_ATTEMPTED_FILE = (0, import_node_path2.join)(SUPERMEMORY_DIR2, ".auth-attempted");
var LOGGED_OUT_FILE = (0, import_node_path2.join)(SUPERMEMORY_DIR2, ".logged-out");
var CONFIG_FILE = (0, import_node_path2.join)((0, import_node_os2.homedir)(), ".codex", "supermemory.json");
function removeFile(path) {
  try {
    if (!(0, import_node_fs.existsSync)(path)) return false;
    (0, import_node_fs.unlinkSync)(path);
    return true;
  } catch (error) {
    console.error(`Failed to remove ${path}: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  }
}
function removeConfigApiKey() {
  try {
    if (!(0, import_node_fs.existsSync)(CONFIG_FILE)) return false;
    const parsed = JSON.parse((0, import_node_fs.readFileSync)(CONFIG_FILE, "utf-8"));
    if (!Object.prototype.hasOwnProperty.call(parsed, "apiKey")) return false;
    delete parsed.apiKey;
    (0, import_node_fs.writeFileSync)(CONFIG_FILE, `${JSON.stringify(parsed, null, 2)}
`);
    return true;
  } catch (error) {
    console.error(`Failed to update ${CONFIG_FILE}: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  }
}
function main() {
  const removedCredentials = removeFile(CREDENTIALS_FILE);
  const removedAuthMarker = removeFile(AUTH_ATTEMPTED_FILE);
  const removedConfigApiKey = removeConfigApiKey();
  const envApiKeySet = !!process.env.SUPERMEMORY_CODEX_API_KEY;
  (0, import_node_fs.mkdirSync)(SUPERMEMORY_DIR2, { recursive: true });
  (0, import_node_fs.writeFileSync)(LOGGED_OUT_FILE, (/* @__PURE__ */ new Date()).toISOString());
  if (removedCredentials || removedConfigApiKey || removedAuthMarker) {
    console.log("Logged out of Supermemory for Codex.");
  } else {
    console.log("No saved Supermemory login was found.");
  }
  if (removedCredentials) {
    console.log(`Removed credentials file: ${CREDENTIALS_FILE}`);
  }
  if (removedConfigApiKey) {
    console.log(`Removed apiKey from ${CONFIG_FILE}`);
  }
  if (envApiKeySet) {
    console.log("");
    console.log("SUPERMEMORY_CODEX_API_KEY is still set in this shell, so memory may remain active until you unset it or restart Codex.");
  } else {
    console.log("Supermemory memory is inactive until you run /supermemory-login again.");
    console.log("This only logs out this local Codex install. To revoke the account-level Codex integration key, disconnect it from the Supermemory integrations page.");
  }
}
main();
