#!/usr/bin/env python3
"""Shared utilities for harness-workflow scripts.

Provides state management, language detection, build command discovery,
and subprocess execution helpers used across all harness scripts.
"""

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Lazy YAML import — PyYAML is optional
try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

# -- State Management --


def load_state(project_dir: Path) -> Optional[Dict[str, Any]]:
    """Load .harness/state.json. Returns None if not found or invalid."""
    state_path = project_dir / ".harness" / "state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_state(project_dir: Path, state: Dict[str, Any]) -> None:
    """Write .harness/state.json with updated timestamp."""
    state_path = project_dir / ".harness" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


# -- Language Detection --

LANGUAGE_MARKERS: List[Tuple[str, List[str]]] = [
    ("typescript", ["tsconfig.json"]),
    ("javascript", ["package.json"]),
    ("python", ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"]),
    ("go", ["go.mod"]),
    ("java", ["pom.xml", "build.gradle", "build.gradle.kts"]),
    ("rust", ["Cargo.toml"]),
    ("csharp", ["*.csproj", "*.sln"]),
    ("ruby", ["Gemfile"]),
    ("php", ["composer.json"]),
]


def detect_language(project_dir: Path) -> Optional[str]:
    """Detect project language by checking marker files in specificity order."""
    for language, markers in LANGUAGE_MARKERS:
        for pattern in markers:
            if list(project_dir.glob(pattern)):
                return language
    return None


# -- Package Manager Detection --

PACKAGE_MANAGER_MARKERS: List[Tuple[str, List[str]]] = [
    ("pnpm", ["pnpm-lock.yaml"]),
    ("yarn", ["yarn.lock"]),
    ("npm", ["package-lock.json"]),
    ("bun", ["bun.lockb", "bun.lock"]),
    ("uv", ["uv.lock"]),
    ("poetry", ["poetry.lock"]),
    ("pip", ["requirements.txt", "Pipfile.lock"]),
    ("go-mod", ["go.sum"]),
    ("cargo", ["Cargo.lock"]),
]


def detect_package_manager(project_dir: Path, language: str) -> Optional[str]:
    """Detect package manager from lock files, with language-aware fallbacks."""
    if language in ("go", "rust"):
        return {"go": "go-mod", "rust": "cargo"}.get(language)

    for pm, markers in PACKAGE_MANAGER_MARKERS:
        for pattern in markers:
            if list(project_dir.glob(pattern)):
                return pm

    fallbacks = {
        "typescript": "npm",
        "javascript": "npm",
        "python": "pip",
        "java": "maven",
        "ruby": "bundler",
        "php": "composer",
    }
    return fallbacks.get(language)


# -- Build Command Detection --


def _check_package_scripts(project_dir: Path) -> Dict[str, str]:
    """Extract lint/typecheck/test commands from package.json scripts."""
    commands: Dict[str, str] = {}
    pkg_path = project_dir / "package.json"
    if not pkg_path.exists():
        return commands
    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        scripts = pkg.get("scripts", {})
        mapping = {
            "lint": "lint",
            "typecheck": "typecheck",
            "check": "check",
            "test": "test",
            "test:unit": "test:unit",
            "test:e2e": "test:e2e",
        }
        for key, script_name in mapping.items():
            if script_name in scripts:
                commands[key] = f"npm run {script_name}"
    except (json.JSONDecodeError, OSError):
        pass
    return commands


def _check_pyproject(project_dir: Path) -> Dict[str, str]:
    """Extract lint/typecheck/test from pyproject.toml tool sections."""
    commands: Dict[str, str] = {}
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return commands
    try:
        content = pyproject.read_text(encoding="utf-8")
        if "[tool.ruff" in content:
            commands["lint"] = "ruff check ."
        if "[tool.mypy" in content:
            commands["typecheck"] = "mypy ."
        if "[tool.pytest" in content:
            commands["test"] = "pytest"
    except OSError:
        pass
    return commands


def _check_makefile(project_dir: Path) -> Dict[str, str]:
    """Extract commands from Makefile targets."""
    commands: Dict[str, str] = {}
    makefile = project_dir / "Makefile"
    if not makefile.exists():
        return commands
    try:
        content = makefile.read_text(encoding="utf-8")
        for target in ("lint", "typecheck", "test", "check"):
            if f"{target}:" in content:
                commands[target] = f"make {target}"
    except OSError:
        pass
    return commands


def _language_defaults(project_dir: Path, language: str) -> Dict[str, str]:
    """Standard build commands per language, used as fallbacks."""
    defaults: Dict[str, str] = {}

    if language == "typescript":
        defaults["lint"] = "npx eslint ."
        defaults["typecheck"] = "npx tsc --noEmit"
        pkg = project_dir / "package.json"
        test_cmd = "npx jest --no-cache"
        if pkg.exists():
            try:
                if "vitest" in pkg.read_text(encoding="utf-8"):
                    test_cmd = "npx vitest run"
            except OSError:
                pass
        defaults["test"] = test_cmd
        defaults["test_unit"] = test_cmd

    elif language == "javascript":
        defaults["lint"] = "npx eslint ."
        defaults["test"] = "npm test"
        defaults["test_unit"] = "npm test"

    elif language == "python":
        defaults["lint"] = "ruff check ."
        defaults["typecheck"] = "mypy ."
        defaults["test"] = "pytest"
        defaults["test_unit"] = "pytest"

    elif language == "go":
        defaults["lint"] = "golangci-lint run"
        defaults["typecheck"] = "go vet ./..."
        defaults["test"] = "go test ./..."
        defaults["test_unit"] = "go test ./... -short"

    elif language == "java":
        defaults["lint"] = "./mvnw spotless:check"
        defaults["typecheck"] = "./mvnw compile"
        defaults["test"] = "./mvnw test"
        defaults["test_unit"] = "./mvnw test"

    elif language == "rust":
        defaults["lint"] = "cargo clippy -- -D warnings"
        defaults["typecheck"] = "cargo check"
        defaults["test"] = "cargo test"
        defaults["test_unit"] = "cargo test --lib"

    elif language == "csharp":
        defaults["lint"] = "dotnet format --verify-no-changes --no-restore"
        defaults["typecheck"] = "dotnet build --no-restore"
        defaults["test"] = "dotnet test --no-build"
        defaults["test_unit"] = "dotnet test --no-build"

    return defaults


def detect_build_commands(project_dir: Path, language: str) -> Dict[str, str]:
    """Detect lint, typecheck, and test commands.

    Checks package.json scripts, pyproject.toml, Makefile, then falls back
    to language-specific standard commands.
    """
    commands: Dict[str, str] = {}

    if language in ("typescript", "javascript"):
        commands.update(_check_package_scripts(project_dir))
    elif language == "python":
        commands.update(_check_pyproject(project_dir))

    commands.update(_check_makefile(project_dir))

    for key, cmd in _language_defaults(project_dir, language).items():
        if key not in commands:
            commands[key] = cmd

    # Apply framework-specific overrides
    commands = _apply_framework_overrides(commands, project_dir, language)

    return commands


def _apply_framework_overrides(
    commands: Dict[str, str], project_dir: Path, language: str
) -> Dict[str, str]:
    """Override build commands based on detected framework and tooling."""
    framework = detect_framework(project_dir, language)

    # Next.js: use built-in lint command
    if framework == "next.js" and "lint" in commands:
        commands["lint"] = "npx next lint"

    # Detect E2E test framework and Prettier from package.json
    if language in ("typescript", "javascript"):
        pkg = project_dir / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                if "@playwright/test" in deps:
                    commands["test_e2e"] = "npx playwright test"
                elif "cypress" in deps:
                    commands["test_e2e"] = "npx cypress run"
            except (json.JSONDecodeError, OSError):
                pass

    return commands


# -- OpenSpec CLI Detection --


def detect_openspec_cli() -> bool:
    """Check if OpenSpec CLI is available on PATH."""
    return shutil.which("openspec") is not None


# -- Subprocess Execution --


def run_command(cmd: str, cwd: Path, timeout: int = 120) -> Dict[str, Any]:
    """Run a shell command and return structured result.

    Returns:
        Dict with keys: success, stdout, stderr, returncode
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


# -- Result Formatting --


def format_result(
    status: str, message: str, details: Optional[Any] = None
) -> Dict[str, Any]:
    """Create a structured result dict."""
    result: Dict[str, Any] = {"status": status, "message": message}
    if details is not None:
        result["details"] = details
    return result


# -- Harness Config Loading --


def load_harness_config(project_dir: Path) -> Optional[Dict[str, Any]]:
    """Load and parse .harness/config.yaml.

    Returns parsed config dict if file exists and PyYAML is available,
    otherwise None. Falls back to JSON parse if YAML unavailable.
    """
    config_path = project_dir / ".harness" / "config.yaml"
    if not config_path.exists():
        return None

    content = config_path.read_text(encoding="utf-8")

    if yaml is not None:
        try:
            return yaml.safe_load(content)
        except Exception:
            return None

    # Fallback: return None with warning (YAML needed for config)
    return None


def get_build_commands_from_config(
    config: Optional[Dict[str, Any]], language: Optional[str] = None
) -> Dict[str, str]:
    """Extract build commands from harness config.

    Checks config.build_verify_loop.stages for command overrides,
    then falls back to auto-detection.
    """
    if not config:
        return {}

    commands: Dict[str, str] = {}

    # Check build_verify_loop.stages for command overrides
    bvl = config.get("build_verify_loop", {})
    if isinstance(bvl, dict):
        stages = bvl.get("stages", [])
        if isinstance(stages, list):
            stage_map = {"lint": "lint", "unit_test": "test", "integration_test": "test", "e2e_test": "test_e2e"}
            for stage in stages:
                if not isinstance(stage, dict):
                    continue
                name = stage.get("name", "")
                cmd = stage.get("command", "")
                if name in stage_map and cmd:
                    commands[stage_map[name]] = cmd

    # Check quality_gates.gates for additional commands
    qg = config.get("workflow", {}).get("quality_gates", {})
    if isinstance(qg, dict):
        gates = qg.get("gates", [])
        if isinstance(gates, list):
            gate_map = {"lint": "lint", "typecheck": "typecheck", "test": "test", "security": "security"}
            for gate in gates:
                if not isinstance(gate, dict):
                    continue
                name = gate.get("name", "")
                cmd = gate.get("command", "")
                if name in gate_map and cmd and name not in commands:
                    commands[gate_map[name]] = cmd

    return commands


# -- Framework Detection --

FRAMEWORK_CONFIG_FILES = {
    "next.js": ["next.config.js", "next.config.mjs", "next.config.ts"],
    "vue": ["vue.config.js", "nuxt.config.ts", "nuxt.config.js"],
    "django": ["manage.py"],
}


def detect_framework(project_dir: Path, language: str) -> Optional[str]:
    """Detect project framework from config files and dependencies."""
    for fw, markers in FRAMEWORK_CONFIG_FILES.items():
        for pattern in markers:
            if list(project_dir.glob(pattern)):
                return fw

    if language in ("typescript", "javascript"):
        pkg = project_dir / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                for name in ("next", "react", "vue", "express"):
                    if name in deps:
                        return {"next": "next.js", "react": "react", "vue": "vue", "express": "express"}[name]
            except (json.JSONDecodeError, OSError):
                pass

    if language == "python":
        reqs = project_dir / "requirements.txt"
        if reqs.exists():
            try:
                content = reqs.read_text(encoding="utf-8").lower()
                for name in ("django", "fastapi", "flask"):
                    if name in content:
                        return name
            except OSError:
                pass

    if language == "csharp":
        for csproj in project_dir.glob("*.csproj"):
            try:
                content = csproj.read_text(encoding="utf-8").lower()
                if "microsoft.aspnetcore" in content or "aspnetcore" in content:
                    return "asp.net"
            except OSError:
                pass

    return None
