"""Claude Code hook for the agent rule in CLAUDE.md "Agents".

Wired in `.claude/settings.json`. It lets the lead run the agents in `.claude/agents/`, one
instance of each at a time, and sends every other agent and the Workflow tool to Ali's prompt.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
# A dispatch that never started (refused at the prompt, or failed) frees its agent after this.
CLAIM_SECONDS = 120


def project_agents() -> set[str]:
    """The `name` of every agent file, which is the name the Agent tool is called with."""
    names = set()
    for path in AGENTS_DIR.glob("*.md"):
        found = re.search(r"^name:\s*(\S+)", path.read_text(encoding="utf-8"), re.MULTILINE)
        if found:
            names.add(found.group(1))
    return names


def state_dir(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / "claude-agent-guard" / session_id


def file_stem(agent: str) -> str:
    return re.sub(r"[^\w-]", "_", agent)


def decision(kind: str, reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": kind,
            "permissionDecisionReason": reason,
        }
    }


def pre_tool_use(event: dict[str, Any], state: Path) -> dict[str, Any] | None:
    if event["tool_name"] == "Workflow":
        return decision(
            "ask",
            "The Workflow tool starts agents that are not in .claude/agents "
            '(CLAUDE.md "Agents"). Ali allows it for this one call or refuses.',
        )
    agent = event["tool_input"].get("subagent_type") or "general-purpose"
    if agent not in project_agents():
        return decision(
            "ask",
            f"'{agent}' is not an agent in .claude/agents (CLAUDE.md \"Agents\"). "
            "Ali allows it for this one call or refuses.",
        )
    stem = file_stem(agent)
    busy = decision(
        "deny",
        f"'{agent}' is already running, and only one instance of an agent runs at a time "
        '(CLAUDE.md "Agents"). Wait for it to finish, or send it a message. If it is not '
        f"running, tell Ali: its marker is in {state}.",
    )
    if any(state.glob(f"{stem}.*.run")):
        return busy
    state.mkdir(parents=True, exist_ok=True)
    claim = state / f"{stem}.claim"
    if claim.exists() and time.time() - claim.stat().st_mtime > CLAIM_SECONDS:
        claim.unlink(missing_ok=True)
    try:
        claim.touch(exist_ok=False)
    except FileExistsError:
        return busy
    return None


def main() -> None:
    event = json.load(sys.stdin)
    state = state_dir(event["session_id"])
    name = event["hook_event_name"]
    if name == "PreToolUse":
        answer = pre_tool_use(event, state)
        if answer:
            print(json.dumps(answer))
    elif name == "SubagentStart":
        stem = file_stem(event["agent_type"])
        state.mkdir(parents=True, exist_ok=True)
        (state / f"{stem}.{event['agent_id']}.run").touch()
        (state / f"{stem}.claim").unlink(missing_ok=True)
    elif name == "SubagentStop":
        stem = file_stem(event["agent_type"])
        (state / f"{stem}.{event['agent_id']}.run").unlink(missing_ok=True)
    elif name == "SessionStart" and state.is_dir():
        # A resumed session has no agent still running.
        for marker in state.iterdir():
            marker.unlink()


if __name__ == "__main__":
    main()
