"""ServeCommand — optional HTTP API server for OpenClaw Agent Mode."""

from __future__ import annotations

import json
from pathlib import Path

from ink_core.cli.builtin import BuiltinCommand
from ink_core.skills.base import SkillResult


class ServeCommand(BuiltinCommand):
    """Start a local HTTP server exposing /log, /recall, /health (agent mode only)."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    @property
    def name(self) -> str:
        return "serve"

    def run(self, target: str | None, params: dict) -> SkillResult:
        from ink_core.core.config import InkConfig

        config = InkConfig(workspace_root=self._root)
        config.load()

        if config.get("mode") != "agent":
            return SkillResult(
                success=False,
                message="ink serve requires agent mode. Set mode: agent in .ink/config.yaml",
            )

        if not config.get("agent.http_api.enabled"):
            return SkillResult(
                success=False,
                message=(
                    "HTTP API is disabled. "
                    "Set agent.http_api.enabled: true in config"
                ),
            )

        port = int(config.get("agent.http_api.port", 4242))
        agent_name = config.get("agent.agent_name", "OpenClaw")

        print(f"Starting ink HTTP API on port {port} (agent: {agent_name})")
        print("Endpoints: POST /log  POST /recall  GET /health")
        print("Press Ctrl+C to stop.")

        self._serve(port, agent_name)
        return SkillResult(success=True, message="Server stopped.")

    # ------------------------------------------------------------------

    def _serve(self, port: int, agent_name: str) -> None:
        import http.server
        import socketserver

        root = self._root

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):  # suppress default access log
                pass

            def do_GET(self):
                if self.path == "/health":
                    self._json(200, {"status": "ok", "mode": "agent", "agent_name": agent_name})
                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(length)
                try:
                    body = json.loads(body_bytes) if body_bytes else {}
                except json.JSONDecodeError:
                    self._json(400, {"error": "invalid JSON body"})
                    return

                if self.path == "/log":
                    self._handle_log(body)
                elif self.path == "/recall":
                    self._handle_recall(body)
                else:
                    self._json(404, {"error": "not found"})

            def _handle_log(self, body: dict):
                content = body.get("content")
                if not content:
                    self._json(400, {"error": "content is required"})
                    return
                from ink_core.agent.commands.log_command import LogCommand
                cmd = LogCommand(root)
                result = cmd.run(content, {"category": body.get("category", "")})
                self._json(200 if result.success else 400,
                           {"success": result.success, "message": result.message})

            def _handle_recall(self, body: dict):
                query = body.get("query")
                if query is None:
                    self._json(400, {"error": "query is required"})
                    return
                from ink_core.agent.commands.recall_command import RecallCommand
                cmd = RecallCommand(root)
                params = {
                    k: body[k] for k in ("category", "since", "limit") if k in body
                }
                result = cmd.run(query, params)
                if result.success:
                    self._json(200, result.data)
                else:
                    self._json(400, {"error": result.message})

            def _json(self, code: int, data: dict):
                payload = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()
