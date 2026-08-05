"""Version consistency + API/CLI surface tests."""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import web.app as app  # noqa: E402
from engine.version import __version__, get_version_info  # noqa: E402

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _version_file() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip().splitlines()[0]


class TestVersionConsistency:
    def test_version_file_is_semver(self):
        assert SEMVER.match(_version_file())

    def test_engine_version_matches_version_file(self):
        assert __version__ == _version_file()

    def test_frontend_package_version_in_sync(self):
        pkg = json.loads((ROOT / "web" / "frontend" / "package.json").read_text())
        assert pkg["version"] == _version_file()

    def test_version_info_shape(self):
        info = get_version_info().as_dict()
        assert info["name"] == "aureon"
        assert info["version"] == __version__
        assert isinstance(info["commit"], str)
        assert isinstance(info["build_time"], str)
        assert isinstance(info["dirty"], bool)
        assert isinstance(info["python"], str)


class TestApiSurface:
    def test_api_version_endpoint(self):
        client = app.app.test_client()
        resp = client.get("/api/version")
        assert resp.status_code == 200
        body = json.loads(resp.data)
        assert body["version"] == __version__
        assert body["name"] == "aureon"

    def test_api_config_includes_app_version(self):
        client = app.app.test_client()
        body = json.loads(client.get("/api/config").data)
        assert body["app_version"] == __version__


class TestCliSurface:
    def test_cli_reports_version(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "cli.py"), "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0
        assert __version__ in proc.stdout


class TestBumpScript:
    @staticmethod
    def _load_module():
        spec = importlib.util.spec_from_file_location(
            "bump_version", ROOT / "scripts" / "bump_version.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_next_version_logic(self):
        mod = self._load_module()
        assert mod.next_version("0.1.0", "patch") == "0.1.1"
        assert mod.next_version("0.1.0", "minor") == "0.2.0"
        assert mod.next_version("0.1.0", "major") == "1.0.0"
        assert mod.next_version("2.9.9", "minor") == "2.10.0"
        assert mod.next_version("2.9.9", "major") == "3.0.0"

    def test_dry_run_changes_nothing(self, tmp_path):
        mod = self._load_module()
        mod.ROOT = tmp_path
        mod.VERSION_FILE = tmp_path / "VERSION"
        mod.PACKAGE_JSON = tmp_path / "package.json"
        mod.VERSION_FILE.write_text("0.1.0\n", encoding="utf-8")
        mod.PACKAGE_JSON.write_text(
            json.dumps({"name": "aureon-frontend", "version": "0.1.0"}),
            encoding="utf-8",
        )
        rc = mod.main(["--patch", "--dry-run"])
        assert rc == 0
        assert mod.VERSION_FILE.read_text().strip() == "0.1.0"
        assert mod.current() == "0.1.0"

    def test_set_writes_version_file_and_package_json(self, tmp_path):
        mod = self._load_module()
        mod.ROOT = tmp_path
        mod.VERSION_FILE = tmp_path / "VERSION"
        mod.PACKAGE_JSON = tmp_path / "package.json"
        mod.VERSION_FILE.write_text("0.1.0\n", encoding="utf-8")
        mod.PACKAGE_JSON.write_text(
            json.dumps({"name": "aureon-frontend", "version": "0.1.0"}),
            encoding="utf-8",
        )
        rc = mod.main(["--set", "0.3.0"])
        assert rc == 0
        assert mod.VERSION_FILE.read_text().strip() == "0.3.0"
        assert json.loads(mod.PACKAGE_JSON.read_text())["version"] == "0.3.0"

    def test_tag_refuses_non_release_branch(self, tmp_path, monkeypatch):
        mod = self._load_module()
        mod.ROOT = tmp_path
        mod.VERSION_FILE = tmp_path / "VERSION"
        mod.PACKAGE_JSON = tmp_path / "package.json"
        mod.VERSION_FILE.write_text("0.1.0\n", encoding="utf-8")
        mod.PACKAGE_JSON.write_text(
            json.dumps({"name": "aureon-frontend", "version": "0.1.0"}),
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "current_branch", lambda: "dev")
        rc = mod.main(["--patch", "--tag"])
        assert rc == 1
        assert mod.VERSION_FILE.read_text().strip() == "0.1.0"
        assert json.loads(mod.PACKAGE_JSON.read_text())["version"] == "0.1.0"
