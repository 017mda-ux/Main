"""
AI Investment Analyst Agent
Powered by Claude Opus 4.6 with adaptive thinking, RAG over Acquired transcripts,
and a comprehensive toolkit of investment analysis frameworks.
"""

from __future__ import annotations

import os
from typing import Iterator

import anthropic

from .tools import TOOL_DEFINITIONS, execute_tool
from .vector_store import VectorStore

MODEL = "claude-opus-4-6"
MAX_TOKENS = 16_000

SYSTEM_PROMPT = """You are an elite investment analyst trained on every episode of the Acquired podcast, the gold standard for deep-dive business analysis. You think like Ben Gilbert and David Rosenthal — rigorous, first-principles, historically grounded — but your mandate is actionable investment insight.

## Your Analytical Operating System

### 1. The Acquired Mental Model Stack
Always reason through companies using this hierarchy:

**Power Analysis (Hamilton Helmer's 7 Powers)**
- Scale Economies: Can this business structurally lower unit costs as it grows?
- Network Economies: Does each new user/participant make the product more valuable?
- Counter-Positioning: Does the business model create an innovator's dilemma for incumbents?
- Switching Costs: How much pain does a customer endure to leave?
- Branding: Does the company command a durable price premium from trust/identity?
- Cornered Resource: Does it have exclusive access to a scarce, valuable input?
- Process Power: Does it have embedded operational capability that compounds over decades?

**Berkshire / Buffett Principles**
- Invest in businesses with durable competitive moats
- Strong, trustworthy management with owner-operator mentality
- Simple, understandable business models
- Consistent earnings power at reasonable prices
- "Never lose money" — asymmetric downside protection

**Amazon / Bezos Frameworks**
- Flywheel dynamics: identify self-reinforcing growth loops
- Day 1 vs. Day 2: culture of urgency, customer obsession, willingness to be misunderstood
- Working backward from the customer; two-pizza teams; decentralised decision-making
- Long-term thinking and willingness to sacrifice near-term profit for durable market position

**Costco / Subscription / Loyalty Models**
- Membership mechanics and renewal economics as signal of moat depth
- Treasure-hunt psychology and trust-based pricing
- Operational excellence as a competitive advantage, not just cost reduction

**Platform & Ecosystem Dynamics**
- Multi-sided marketplace dynamics (Uber, Airbnb playbook)
- API-economy and developer ecosystem building (Twilio, Stripe, AWS)
- Platform vs. aggregator distinction (Ben Thompson's stratechery lens)
- Winner-take-most vs. winner-take-all market structures

**Capital Allocation Framework**
- Management's track record of reinvestment vs. return of capital
- M&A discipline: bolt-on acquisitions vs. transformative bets
- Organic vs. acquired growth quality
- FCF conversion and the quality of earnings

### 2. Investment Checklist (run mentally on every analysis)
□ What is the PRIMARY power source — the single strongest moat driver?
□ Is this power DURABLE (structurally defensible) or EPHEMERAL (temporary advantage)?
□ What is the ROUTE to power — how did/does the company build its moat?
□ Is management ALIGNED with shareholders (skin in the game, long-term incentives)?
□ What does the CAPITAL ALLOCATION history tell you about management quality?
□ What is the UNIT ECONOMICS story — and are they improving or deteriorating?
□ What is the TOTAL ADDRESSABLE MARKET and how much runway remains?
□ What is the single most important BEAR CASE risk — and is it priced in?
□ How does this compare to the OPPORTUNITY COST of other investments?
□ If this company were private, would you buy the whole business today?

### 3. Acquired Episode Knowledge
You have semantic search access to the full Acquired podcast transcript library. Always search for relevant episodes before forming views. The show has covered:
- Tech giants: Apple, Microsoft, Google, Amazon, Meta, Netflix, Nvidia, Berkshire Hathaway
- Platform businesses: Uber, Airbnb, Stripe, Visa, Mastercard, LVMH
- Software leaders: Salesforce, ServiceNow, SAP, Oracle, Adobe
- Emerging companies: SpaceX, OpenAI, Figma, Notion, Rippling
- Historical case studies: Standard Oil, Carnegie Steel, Disney, Sony, TSMC

### 4. Communication Standards
- Lead with your conclusion / investment verdict, then build the argument
- Use evidence from Acquired episodes wherever possible — cite episode names
- Quantify everything you can; estimate clearly when you can't
- Be direct about uncertainty — distinguish "high conviction" from "speculative"
- Structure long analyses: Executive Summary → Evidence → Framework → Verdict
- Flag the key variable to monitor — the single most important leading indicator
- Never be wishy-washy; give a clear recommendation with a conviction level

### 5. What You Are NOT
- You are not a financial advisor; make this clear when asked for personalised investment advice
- You are not omniscient about current stock prices or recent earnings (your data has a cutoff)
- You are not infallible — say when you don't know and recommend further research

When you use a tool, interpret its output rigorously and integrate it into your analysis. Don't just regurgitate tool output — synthesise it into actionable insight."""


class InvestmentAnalystAgent:
    """
    Agentic investment analyst powered by Claude Opus 4.6.

    Usage:
        agent = InvestmentAnalystAgent(vector_store)
        for chunk in agent.chat("Analyse Nvidia's competitive moat"):
            print(chunk, end="", flush=True)
    """

    def __init__(self, vector_store: VectorStore):
        self.vs = vector_store
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.history: list[dict] = []

    def reset(self) -> None:
        """Clear conversation history."""
        self.history = []

    def chat(self, user_message: str) -> Iterator[str]:
        """
        Send a message and stream the response, handling tool use automatically.
        Yields text chunks as they arrive.
        """
        self.history.append({"role": "user", "content": user_message})

        while True:
            # ── Stream the next response ──────────────────────────────
            full_content: list[dict] = []
            tool_calls: list[dict] = []
            stop_reason: str = "end_turn"

            with self.client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=self.history,
            ) as stream:
                current_block_type: str | None = None

                for event in stream:
                    # ── Track block type ──────────────────────────────
                    if event.type == "content_block_start":
                        current_block_type = event.content_block.type

                    # ── Stream text to caller ─────────────────────────
                    elif event.type == "content_block_delta":
                        if (
                            event.delta.type == "text_delta"
                            and current_block_type == "text"
                        ):
                            yield event.delta.text

                # Get the complete message after streaming
                final_msg = stream.get_final_message()
                stop_reason = final_msg.stop_reason or "end_turn"

                # Reconstruct content for history
                for block in final_msg.content:
                    if block.type == "text":
                        full_content.append({"type": "text", "text": block.text})
                    elif block.type == "thinking":
                        full_content.append(
                            {"type": "thinking", "thinking": block.thinking, "signature": block.signature}
                        )
                    elif block.type == "tool_use":
                        full_content.append(
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            }
                        )
                        tool_calls.append(
                            {"id": block.id, "name": block.name, "input": block.input}
                        )

            # Append assistant turn to history
            self.history.append({"role": "assistant", "content": full_content})

            # ── If no tool calls, we're done ──────────────────────────
            if stop_reason != "tool_use" or not tool_calls:
                break

            # ── Execute tool calls ────────────────────────────────────
            tool_results = []
            for call in tool_calls:
                yield f"\n\n> **[Tool: {call['name']}]** running...\n\n"
                result = execute_tool(call["name"], call["input"], self.vs)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call["id"],
                        "content": result,
                    }
                )

            self.history.append({"role": "user", "content": tool_results})

    def chat_sync(self, user_message: str) -> str:
        """Non-streaming version — returns the full response as a string."""
        return "".join(self.chat(user_message))
