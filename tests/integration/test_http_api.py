"""Integration tests for ServeCommand HTTP API.

Tests:
- GET  /health         → {status, mode, agent_name}
- POST /log            → happy path + missing content → 400
- POST /recall         → happy path + missing query → 400
- GET  /unknown        → 404
- ink serve refused when mode != agent
- ink serve refused when http_api.enabled = false
"""
from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

from ink_core.agent.commands.serve_command import ServeCommand

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _make_agent_workspace(root: Path, port: int) -> Path:
    ws = root / "ws"
    ws.mkdir(exist_ok=True)
    (ws / ".ink").mkdir(exist_ok=True)
    cfg = {
        "mode": "agent",
        "git": {"auto_commit": False},
        "agent": {
            "agent_name": "TestAgent",
            "http_api": {"enabled": True, "port": port},
        },
    }
    (ws / ".ink" / "config.yaml").write_text(yaml.dump(cfg), encoding="utf-8")
    return ws


def _wait_for_server(port: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.05)
    return False


def _http_get(port: int, path: str) -> tuple[int, dict]:
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _http_post(port: int, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(data)),
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def running_server(tmp_path_factory: pytest.TempPathFactory):
    """Start ServeCommand HTTP server in a daemon thread; yield (port, workspace)."""
    tmp_path = tmp_path_factory.mktemp("http_api")
    port = _find_free_port()
    ws = _make_agent_workspace(tmp_path, port)
    cmd = ServeCommand(ws)

    thread = threading.Thread(target=cmd.run, args=(None, {}), daemon=True)
    thread.start()

    assert _wait_for_server(port, timeout=5.0), "HTTP server did not start in time"
    yield port, ws
    # Daemon thread terminates with the test process


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health_endpoint_returns_ok(running_server) -> None:
    """GET /health returns {status: ok, mode: agent, agent_name: TestAgent}."""
    port, _ = running_server
    status, body = _http_get(port, "/health")
    assert status == 200
    assert body["status"] == "ok"
    assert body["mode"] == "agent"
    assert body["agent_name"] == "TestAgent"


def test_log_happy_path(running_server) -> None:
    """POST /log with valid content and category returns 200 success."""
    port, _ = running_server
    status, body = _http_post(port, "/log", {"content": "hello world", "category": "note"})
    assert status == 200
    assert body["success"] is True


def test_log_missing_content_returns_400(running_server) -> None:
    """POST /log without content returns HTTP 400 with error message."""
    port, _ = running_server
    status, body = _http_post(port, "/log", {})
    assert status == 400
    assert "content" in body.get("error", "").lower()


def test_recall_happy_path(running_server) -> None:
    """POST /recall with a query string returns 200 with entries list."""
    port, _ = running_server
    # Pre-log an entry so recall has something to find
    _http_post(port, "/log", {"content": "recall test entry", "category": "note"})
    status, body = _http_post(port, "/recall", {"query": "recall"})
    assert status == 200
    assert "entries" in body
    assert isinstance(body["entries"], list)


def test_recall_empty_query_returns_all(running_server) -> None:
    """POST /recall with empty query string returns all entries."""
    port, _ = running_server
    status, body = _http_post(port, "/recall", {"query": ""})
    assert status == 200
    assert "entries" in body
    assert isinstance(body["entries"], list)


def test_recall_missing_query_returns_400(running_server) -> None:
    """POST /recall without query field returns HTTP 400."""
    port, _ = running_server
    status, body = _http_post(port, "/recall", {})
    assert status == 400
    assert "query" in body.get("error", "").lower()


def test_unknown_get_endpoint_returns_404(running_server) -> None:
    """GET on an unregistered path returns 404."""
    port, _ = running_server
    status, body = _http_get(port, "/unknown-path")
    assert status == 404


def test_unknown_post_endpoint_returns_404(running_server) -> None:
    """POST on an unregistered path returns 404."""
    port, _ = running_server
    status, body = _http_post(port, "/unknown-path", {"x": 1})
    assert status == 404


def test_serve_refused_when_not_agent_mode(tmp_path: Path) -> None:
    """ServeCommand.run() returns SkillResult(success=False) when mode != agent."""
    (tmp_path / ".ink").mkdir()
    (tmp_path / ".ink" / "config.yaml").write_text(
        yaml.dump({"mode": "human"}), encoding="utf-8"
    )
    cmd = ServeCommand(tmp_path)
    result = cmd.run(None, {})
    assert result.success is False
    assert "agent mode" in result.message.lower()


def test_serve_refused_when_http_api_disabled(tmp_path: Path) -> None:
    """ServeCommand.run() returns SkillResult(success=False) when http_api.enabled=false."""
    (tmp_path / ".ink").mkdir()
    (tmp_path / ".ink" / "config.yaml").write_text(
        yaml.dump({"mode": "agent", "agent": {"http_api": {"enabled": False, "port": 9991}}}),
        encoding="utf-8",
    )
    cmd = ServeCommand(tmp_path)
    result = cmd.run(None, {})
    assert result.success is False
    assert "disabled" in result.message.lower()


def test_log_invalid_json_body_returns_400(running_server) -> None:
    """POST /log with malformed JSON body returns HTTP 400."""
    port, _ = running_server
    url = f"http://127.0.0.1:{port}/log"
    data = b"not-valid-json{"
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Content-Length": str(len(data))},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    assert status == 400
