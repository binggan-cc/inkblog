"""Property tests for human command compatibility guard.

Property 15: disable_human_commands intercept
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from ink_core.cli.intent import Intent, IntentRouter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HUMAN_COMMANDS = ["publish", "build", "search", "analyze", "rebuild"]


def _make_workspace(root: Path, *, mode: str, disable_human: bool) -> Path:
    ws = root / "ws"
    ws.mkdir(exist_ok=True)
    (ws / ".ink").mkdir(exist_ok=True)
    cfg = {
        "mode": mode,
        "agent": {"disable_human_commands": disable_human},
    }
    (ws / ".ink" / "config.yaml").write_text(yaml.dump(cfg), encoding="utf-8")
    return ws


def _make_router(ws: Path) -> IntentRouter:
    mock_registry = MagicMock()
    mock_registry.resolve.return_value = None
    mock_registry.list_all.return_value = []
    return IntentRouter({}, mock_registry, workspace_root=ws)


# ---------------------------------------------------------------------------
# Property 15: disable_human_commands intercept
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", _HUMAN_COMMANDS)
def test_property15_human_command_blocked_in_agent_mode(
    tmp_path: Path, command: str
) -> None:
    """Human commands are blocked when mode=agent and disable_human_commands=true."""
    ws = _make_workspace(tmp_path, mode="agent", disable_human=True)
    router = _make_router(ws)

    route_result = router.resolve(Intent(action=command, target=None))

    # Guard injects a blocking command as the target
    assert route_result.target is not None
    skill_result = route_result.target.run(None, {})
    assert skill_result.success is False
    assert command in skill_result.message
    assert "disabled" in skill_result.message.lower()


@pytest.mark.parametrize("command", _HUMAN_COMMANDS)
def test_property15_human_commands_pass_when_not_disabled(
    tmp_path: Path, command: str
) -> None:
    """Human commands are NOT blocked when disable_human_commands=false (even in agent mode)."""
    ws = _make_workspace(tmp_path, mode="agent", disable_human=False)
    router = _make_router(ws)

    route_result = router.resolve(Intent(action=command, target=None))

    # May resolve to None (not found in empty registry) but must NOT be the guard
    if route_result.target is not None:
        skill_result = route_result.target.run(None, {})
        assert "disabled in agent mode" not in (skill_result.message or "")


@pytest.mark.parametrize("command", _HUMAN_COMMANDS)
def test_property15_human_commands_not_blocked_in_human_mode(
    tmp_path: Path, command: str
) -> None:
    """Human commands are not intercepted when mode=human regardless of disable flag."""
    ws = _make_workspace(tmp_path, mode="human", disable_human=True)
    router = _make_router(ws)

    route_result = router.resolve(Intent(action=command, target=None))

    if route_result.target is not None:
        skill_result = route_result.target.run(None, {})
        assert "disabled in agent mode" not in (skill_result.message or "")


@given(command=st.sampled_from(_HUMAN_COMMANDS))
@settings(max_examples=50)
def test_property15_property_based_all_human_commands_blocked(command: str) -> None:
    """Property: every human command returns success=False when agent mode + disable=true."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ws = _make_workspace(Path(tmp), mode="agent", disable_human=True)
        router = _make_router(ws)
        route_result = router.resolve(Intent(action=command, target=None))

    assert route_result.target is not None
    skill_result = route_result.target.run(None, {})
    assert skill_result.success is False


def test_property15_non_human_commands_not_affected(tmp_path: Path) -> None:
    """Agent-mode commands (log, recall, etc.) are not affected by the human guard."""
    ws = _make_workspace(tmp_path, mode="agent", disable_human=True)
    router = _make_router(ws)

    for agent_cmd in ["log", "recall", "serve", "skill-record", "skill-save", "skill-list"]:
        route_result = router.resolve(Intent(action=agent_cmd, target=None))
        # These are not human commands — guard does not apply
        # They may be "not found" but should not trigger the guard message
        if route_result.target is not None:
            skill_result = route_result.target.run(None, {})
            assert "disabled in agent mode" not in (skill_result.message or "")
