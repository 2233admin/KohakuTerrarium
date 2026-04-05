"""Copilot CLI management: model switching, status checks, AST patch driver."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)

COPILOT_CONFIG_PATH = Path.home() / ".copilot" / "config.json"
COPILOT_MODEL_ENV = "COPILOT_MODEL"

KNOWN_MODELS: list[str] = [
    "gpt-4o",
    "gpt-4.1",
    "gpt-4.1-mini",
    "o3-mini",
    "o4-mini",
    "claude-sonnet-4",
    "claude-sonnet-4-20250514",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
]

# JS snippet for AST patching via meriyah + astring.
# Requires: npm install -g meriyah astring (or local to copilot dir).
PATCH_SCRIPT = """\
const fs = require('fs');
const { parseScript } = require('meriyah');
const { generate } = require('astring');

const bundlePath = process.env.COPILOT_BUNDLE_PATH;
const modelsJson = process.env.COPILOT_PATCH_MODELS || '[]';
const models = JSON.parse(modelsJson);

if (!bundlePath || !fs.existsSync(bundlePath)) {
  console.error('Bundle not found:', bundlePath);
  process.exit(1);
}

// Backup original
const backupPath = bundlePath + '.bak';
if (!fs.existsSync(backupPath)) {
  fs.copyFileSync(bundlePath, backupPath);
}

const src = fs.readFileSync(bundlePath, 'utf8');
const ast = parseScript(src, { ranges: true, next: true });

// Walk AST to find model whitelist arrays and inject new entries
let patched = false;
function walk(node) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) { node.forEach(walk); return; }
  // Look for array expressions containing known model strings
  if (node.type === 'ArrayExpression' && node.elements) {
    const vals = node.elements
      .filter(e => e && e.type === 'Literal' && typeof e.value === 'string')
      .map(e => e.value);
    if (vals.includes('gpt-4o') || vals.includes('gpt-4')) {
      for (const m of models) {
        if (!vals.includes(m)) {
          node.elements.push({ type: 'Literal', value: m });
          patched = true;
        }
      }
    }
  }
  for (const key of Object.keys(node)) {
    if (key === 'type') continue;
    walk(node[key]);
  }
}
walk(ast);

if (patched) {
  fs.writeFileSync(bundlePath, generate(ast));
  console.log('Patch applied successfully');
} else {
  console.log('No model whitelist found to patch');
}
"""


def find_copilot_cli() -> Path | None:
    """Locate the GitHub Copilot CLI binary on PATH or common locations."""
    result = shutil.which("github-copilot-cli")
    if result:
        return Path(result)
    # Windows fallback: check npm global install location
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        win_path = Path(local_app) / "npm" / "github-copilot-cli.cmd"
        if win_path.exists():
            return win_path
    return None


def get_copilot_version() -> str | None:
    """Get the installed Copilot CLI version string, or None if unavailable."""
    cli = find_copilot_cli()
    if cli is None:
        return None
    try:
        result = subprocess.run(
            [str(cli), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("Failed to get Copilot version: %s", exc)
    return None


def get_current_model(config_path: Path | None = None) -> str | None:
    """Get the active Copilot model. Env var takes priority over config file."""
    env_model = os.environ.get(COPILOT_MODEL_ENV)
    if env_model:
        return env_model
    cfg_path = config_path or COPILOT_CONFIG_PATH
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            return data.get("model")
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read copilot config: %s", exc)
    return None


def set_model(model: str, config_path: Path | None = None) -> None:
    """Set the active Copilot model in the config file."""
    cfg_path = config_path or COPILOT_CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}

    data["model"] = model
    cfg_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Copilot model set to '%s' in %s", model, cfg_path)


def list_available_models() -> list[str]:
    """Return a copy of the known Copilot API models list."""
    return list(KNOWN_MODELS)


def copilot_status() -> dict:
    """Return a status dict with installed, version, model, config_path."""
    cli = find_copilot_cli()
    installed = cli is not None
    version = get_copilot_version() if installed else None
    model = get_current_model()
    config_path = str(COPILOT_CONFIG_PATH) if COPILOT_CONFIG_PATH.exists() else None

    return {
        "installed": installed,
        "version": version,
        "model": model,
        "config_path": config_path,
    }


class PatchDriver:
    """Manages AST patching of the Copilot CLI bundle for extended model support."""

    def __init__(self, target: str = "copilot") -> None:
        self.target = target

    def _find_node(self) -> Path | None:
        """Locate the Node.js binary."""
        result = shutil.which("node")
        if result:
            return Path(result)
        return None

    def detect_install(self) -> Path | None:
        """Find the Copilot CLI bundle JS file.

        Checks the CLI location then looks for sibling node_modules
        or standard npm global paths.
        """
        cli = find_copilot_cli()
        if cli is None:
            return None
        # Try to find bundle relative to the CLI binary
        cli_dir = cli.resolve().parent
        # Common patterns for npm global installs
        candidates = [
            cli_dir / "node_modules" / "@githubnext" / "copilot-cli" / "dist" / "index.js",
            cli_dir / ".." / "lib" / "node_modules" / "github-copilot-cli" / "dist" / "index.js",
        ]
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.exists():
                return resolved
        return None

    def is_patched(self) -> bool:
        """Check if the bundle has been patched (backup file exists)."""
        bundle = self.detect_install()
        if bundle is None:
            return False
        return Path(str(bundle) + ".bak").exists()

    def apply_patch(self, models: list[str] | None = None) -> bool:
        """Apply AST patch to add extended model support.

        Returns True on success, False on failure.
        Requires Node.js and meriyah/astring npm packages.
        """
        node = self._find_node()
        if node is None:
            logger.warning("Node.js not found -- cannot apply Copilot patch")
            return False

        bundle = self.detect_install()
        if bundle is None:
            logger.warning("Copilot CLI bundle not found -- cannot patch")
            return False

        patch_models = models or [
            "claude-sonnet-4",
            "claude-sonnet-4-20250514",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
        ]

        env = os.environ.copy()
        env["COPILOT_BUNDLE_PATH"] = str(bundle)
        env["COPILOT_PATCH_MODELS"] = json.dumps(patch_models)

        try:
            subprocess.run(
                [str(node), "-e", PATCH_SCRIPT],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
                env=env,
            )
            logger.info("Copilot patch applied to %s", bundle)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Copilot patch failed: %s", exc)
            return False

    def unpatch(self) -> bool:
        """Restore the original Copilot CLI bundle from backup."""
        bundle = self.detect_install()
        if bundle is None:
            logger.warning("Copilot CLI bundle not found -- cannot unpatch")
            return False

        backup = Path(str(bundle) + ".bak")
        if not backup.exists():
            logger.warning("No backup found at %s", backup)
            return False

        try:
            shutil.copy2(str(backup), str(bundle))
            backup.unlink()
            logger.info("Copilot bundle restored from backup")
            return True
        except OSError as exc:
            logger.warning("Failed to restore Copilot bundle: %s", exc)
            return False
