"""
Nomad-style investment agent.

The system prompt lives in .claude/agents/nomad-investor.md so the same
principles drive both this Python agent and the Claude Code subagent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import anthropic

from .tools import TOOL_DEFINITIONS, execute_tool

MODEL = "claude-opus-5-5"
MAX_TOKENS = 64_000
PROMPT_FILE = Path(__file__).resolve().parent.parent / ".claude" / "agents" / "nomad-investor.md"

PYTHON_AGENT_NOTE = """

## Tools in this environment

You have `web_search` for current figures and six calculators: scale_economies_shared,
retention_quality, unit_economics_persistence, destination_analysis, reverse_valuation and
moat_scorecard. Use the calculators whenever you have numbers rather than doing arithmetic in
your head, and finish full company analyses with moat_scorecard."""


def load_system_prompt(path: Path = PROMPT_FILE) -> str:
    """Read the agent markdown and strip its YAML front matter."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]
    return text.strip() + PYTHON_AGENT_NOTE


def _client_tools() -> list[dict]:
    # Stream tool inputs as they are generated; execute_tool validates them.
    return [{**t, "eager_input_streaming": True} for t in TOOL_DEFINITIONS]


SERVER_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]


class NomadAgent:
    """
    Usage:
        agent = NomadAgent()
        for chunk in agent.chat("Is Costco still sharing its scale economies?"):
            print(chunk, end="", flush=True)
    """

    def __init__(self, client: anthropic.Anthropic | None = None, effort: str = "high"):
        self.client = client or anthropic.Anthropic()
        self.effort = effort
        self.system = load_system_prompt()
        self.tools = _client_tools() + SERVER_TOOLS
        self.history: list = []

    def reset(self) -> None:
        self.history = []

    def chat(self, user_message: str) -> Iterator[str]:
        """Send a message, run tools as needed, and stream the reply text."""
        self.history.append({"role": "user", "content": user_message})

        while True:
            with self.client.beta.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                output_config={"effort": self.effort},
                system=[{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}],
                tools=self.tools,
                messages=self.history,
                betas=["server-side-fallback-2026-07-01"],
                extra_body={"fallbacks": "default"},
            ) as stream:
                for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and getattr(event.delta, "type", None) == "text_delta"
                    ):
                        yield event.delta.text
                final = stream.get_final_message()

            # Keep every block (thinking, server tool results, fallbacks) unchanged.
            self.history.append({"role": "assistant", "content": final.content})

            if final.stop_reason == "refusal":
                yield "\n\n[The model declined this request.]"
                return
            if final.stop_reason == "max_tokens":
                yield "\n\n[Reply hit the length limit.]"
                return
            if final.stop_reason == "pause_turn":
                continue  # server-side search loop paused; resend to resume
            if final.stop_reason != "tool_use":
                return

            results = []
            for block in final.content:
                if block.type != "tool_use":
                    continue
                yield f"\n\n> running {block.name}…\n\n"
                output, is_error = execute_tool(block.name, block.input)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                        "is_error": is_error,
                    }
                )
            # All results for this turn go back in one message.
            self.history.append({"role": "user", "content": results})

    def ask(self, question: str) -> str:
        return "".join(self.chat(question))


def dump_history(agent: NomadAgent) -> str:
    """Debug helper: history as JSON."""
    def enc(o):
        return o.model_dump() if hasattr(o, "model_dump") else str(o)
    return json.dumps(agent.history, default=enc, indent=2)
