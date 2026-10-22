from types import SimpleNamespace as NS

from nomad.agent import NomadAgent


class FakeStream:
    def __init__(self, msg, text=""):
        self.msg, self.text = msg, text

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        if self.text:
            yield NS(type="content_block_delta", delta=NS(type="text_delta", text=self.text))

    def get_final_message(self):
        return self.msg


class FakeMessages:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def stream(self, **kw):
        self.calls.append(kw)
        return self.responses.pop(0)


def test_tool_round_trip():
    tool_msg = NS(stop_reason="tool_use", content=[
        NS(type="tool_use", id="t1", name="reverse_valuation",
           input={"market_cap": 1000, "owner_earnings": 40}),
    ])
    done_msg = NS(stop_reason="end_turn", content=[NS(type="text", text="Verdict")])
    msgs = FakeMessages([FakeStream(tool_msg), FakeStream(done_msg, "Verdict")])
    agent = NomadAgent(client=NS(beta=NS(messages=msgs)))

    out = agent.ask("value it")

    assert "Verdict" in out and "reverse_valuation" in out
    result = agent.history[2]["content"][0]
    assert result["tool_use_id"] == "t1" and result["is_error"] is False
    kw = msgs.calls[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["extra_body"] == {"fallbacks": "default"}
    assert all(t.get("eager_input_streaming") for t in kw["tools"] if "input_schema" in t)


def test_refusal_stops():
    msgs = FakeMessages([FakeStream(NS(stop_reason="refusal", content=[]))])
    agent = NomadAgent(client=NS(beta=NS(messages=msgs)))
    assert "declined" in agent.ask("x")
