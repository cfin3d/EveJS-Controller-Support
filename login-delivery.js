"use strict";

// A mod-specific integration for the reviewed EveJS 0.12.9 handshake.
// No client archive changes, RPCs, input-handler replacements, or server source writes.
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const KEY = Symbol.for("evejs.controller.login.v1");
const BASELINE = "4fc3c37ec83c443c1497a3daba57d7157d05bbe55af3be2d5545b6162398ebc9";
const normalize = source => String(source).replace(/\r\n/g, "\n");
function supports(source) {
  return crypto.createHash("sha256").update(normalize(source)).digest("hex") === BASELINE;
}

// Python 2.7 and 3 compatible; all paths come from the launcher's captured
// client environment. Do not embed a Docker/container path into client code.
const BOOTSTRAP = [
  "try:",
  " import os as _ec_os",
  " _ec_dir = _ec_os.environ.get('CONTROLLER_MOD_DIRECTORY', '')",
  " if _ec_dir and _ec_os.path.isdir(_ec_dir):",
  "  _ec_ui = {'__builtins__': __builtins__}",
  "  _ec_input = {'__builtins__': __builtins__}",
  "  for _ec_file, _ec_namespace in [('client-ui.py', _ec_ui), ('controller.py', _ec_input)]:",
  "   with open(_ec_os.path.join(_ec_dir, _ec_file), 'rb') as _ec_stream:",
  "    _ec_source = _ec_stream.read(65537)",
  "   if len(_ec_source) > 65536: raise ValueError('Oversized controller script')",
  "   eval(compile(_ec_source, '<evejs-controller-runtime>', 'exec'), _ec_namespace)",
  "  _ec_input['start'](_ec_dir, _ec_ui)",
  "except Exception:",
  " print('EVEJS_CONTROLLER_START:FAILED')",
].join("\n");

function compose(original, bootstrap = BOOTSTRAP) {
  if (!Buffer.isBuffer(original) || original.length < 5 || original[0] !== 0x74 || original.readUInt32LE(1) !== original.length - 5) {
    throw new Error("Unsupported login expression envelope");
  }
  if (bootstrap.length > 4096 || original.length > 240 * 1024) throw new Error("Login expression exceeds the supported limit");
  const previous = original.subarray(5).toString("ascii");
  // Base64 carries the authored Python without escape or Unicode ambiguities.
  const source64 = Buffer.from(bootstrap, "utf8").toString("base64");
  const execute = `eval(compile(__import__('base64').b64decode('${source64}'), '<evejs-controller-start>', 'exec'), {'__builtins__': __builtins__})`;
  const wrapped = `(lambda _ec_original_result: (${execute}, _ec_original_result)[1])(${previous})`;
  const data = Buffer.from(wrapped, "ascii");
  if (data.length > 256 * 1024) throw new Error("Combined login expression exceeds the supported limit");
  const header = Buffer.alloc(5); header[0] = 0x74; header.writeUInt32LE(data.length, 1);
  return Buffer.concat([header, data]);
}

function enabled(folder) {
  // Startup must fail closed if the package was disabled, removed, or damaged.
  try { return JSON.parse(fs.readFileSync(path.join(folder, "activation.json"), "utf8")).enabled === true; }
  catch { return false; }
}

function extension() {
  return `
// EveJS Controller: compose after all existing login handlers and preserve their result.
const __ec_previous_login_v1 = buildTidiSignedFunc;
buildTidiSignedFunc = function() {
  const original = __ec_previous_login_v1.apply(this, arguments);
  try {
    const controller = globalThis[Symbol.for("evejs.controller.login.v1")];
    return controller && controller.enabled() ? controller.compose(original) : original;
  } catch (error) {
    console.error("[EveJS Controller] Automatic companion start unavailable; original login preserved.");
    return original;
  }
};
`;
}

function install(root, folder, { Module = require("node:module"), global = globalThis, log = console } = {}) {
  if (global[KEY]) return global[KEY];
  const handshake = path.join(root, "server/src/network/tcp/handshake.js");
  let native;
  try { native = normalize(fs.readFileSync(handshake, "utf8")); }
  catch { log.error("[EveJS Controller] Handshake source missing; mod inactive."); return { active: false }; }
  if (!supports(native)) { log.error("[EveJS Controller] Unsupported handshake; mod inactive."); return { active: false }; }
  const canonical = file => process.platform === "win32" ? path.resolve(file).toLowerCase() : path.resolve(file);
  if (Object.values(require.cache).some(entry => canonical(entry.filename) === canonical(handshake))) {
    log.error("[EveJS Controller] Handshake already loaded; restart the server normally."); return { active: false };
  }
  const previousCompile = Module.prototype._compile;
  Module.prototype._compile = function(content, filename) {
    if (canonical(filename) === canonical(handshake)) {
      // The unchanged reviewed source can have another mod's appended wrapper.
      // Loader ordering lets strict earlier wrappers validate before ours appends.
      if (normalize(content).startsWith(native)) content += extension();
      else log.error("[EveJS Controller] Handshake changed during preload; existing login preserved.");
    }
    return previousCompile.call(this, content, filename);
  };
  const state = { active: true, enabled: () => enabled(folder), compose };
  global[KEY] = state;
  log.log("[EveJS Controller] Login startup ready. Input remains on the Windows client PC.");
  return state;
}

module.exports = { KEY, BASELINE, BOOTSTRAP, normalize, supports, compose, enabled, extension, install };
