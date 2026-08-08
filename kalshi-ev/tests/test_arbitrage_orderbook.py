from kalshi_ev.arbitrage import scan_event
from kalshi_ev.client import Orderbook


def book(ticker, yes_bids, no_bids):
    return Orderbook.from_api(ticker, {"yes": yes_bids, "no": no_bids})


# ── Orderbook view math ──────────────────────────────────────────────


def test_orderbook_derives_asks_from_opposite_bids():
    b = book("T", yes_bids=[[40, 100], [39, 50]], no_bids=[[55, 80]])
    assert b.best_yes_bid == 40
    assert b.best_no_bid == 55
    assert b.best_yes_ask == 45      # 100 - best no bid
    assert b.best_no_ask == 60       # 100 - best yes bid
    assert b.yes_ask_qty == 80
    assert b.no_ask_qty == 100
    assert b.mid_cents == 42.5
    assert b.spread_cents == 5


def test_orderbook_sorts_unordered_levels():
    b = book("T", yes_bids=[[30, 10], [42, 5], [38, 7]], no_bids=[])
    assert b.best_yes_bid == 42
    assert b.best_yes_ask is None
    assert b.mid_cents == 42.0


# ── structural arbs ──────────────────────────────────────────────────


def _event(markets, mutually_exclusive=True):
    return {"event_ticker": "EVT", "mutually_exclusive": mutually_exclusive,
            "markets": markets}


def test_all_yes_arb_detected():
    # 3 MECE buckets whose YES asks sum to 90c: 10c gross, ~8.5c net profit
    markets = [{"ticker": f"M{i}"} for i in range(3)]
    books = {
        "M0": book("M0", yes_bids=[[5, 500]], no_bids=[[80, 500]]),   # yes ask 20
        "M1": book("M1", yes_bids=[[5, 300]], no_bids=[[70, 300]]),   # yes ask 30
        "M2": book("M2", yes_bids=[[5, 200]], no_bids=[[60, 200]]),   # yes ask 40
    }
    opps = [o for o in scan_event(_event(markets), books) if o.kind == "all_yes"]
    assert len(opps) == 1
    opp = opps[0]
    # fees: 0.07*(0.2*0.8 + 0.3*0.7 + 0.4*0.6)*100 = 1.12 + 1.47 + 1.68 = 4.27c
    assert abs(opp.cost_cents - 94.27) < 0.01
    assert abs(opp.profit_cents - 5.73) < 0.01
    assert opp.max_units == 200
    assert opp.assumes_exhaustive


def test_no_arb_when_fees_eat_it():
    # YES asks sum to 99c: 1c gross but ~5c of fees -> not an arb
    markets = [{"ticker": f"M{i}"} for i in range(3)]
    books = {
        "M0": book("M0", yes_bids=[[5, 100]], no_bids=[[67, 100]]),   # 33
        "M1": book("M1", yes_bids=[[5, 100]], no_bids=[[67, 100]]),   # 33
        "M2": book("M2", yes_bids=[[5, 100]], no_bids=[[67, 100]]),   # 33
    }
    assert scan_event(_event(markets), books) == []


def test_all_yes_requires_mutual_exclusivity():
    markets = [{"ticker": "M0"}, {"ticker": "M1"}]
    books = {
        "M0": book("M0", yes_bids=[[5, 100]], no_bids=[[80, 100]]),
        "M1": book("M1", yes_bids=[[5, 100]], no_bids=[[80, 100]]),
    }
    opps = scan_event(_event(markets, mutually_exclusive=False), books)
    assert all(o.kind == "box" for o in opps)


def test_all_no_arb_detected():
    # 3 MECE buckets, NO asks 55c each => cost 165 + fees vs payout 200
    markets = [{"ticker": f"M{i}"} for i in range(3)]
    books = {
        f"M{i}": book(f"M{i}", yes_bids=[[45, 250]], no_bids=[[40, 250]])
        for i in range(3)
    }
    opps = [o for o in scan_event(_event(markets), books) if o.kind == "all_no"]
    assert len(opps) == 1
    opp = opps[0]
    assert opp.payout_cents == 200.0
    # 200 - 165 - 3 * 1.7325 = 29.8c guaranteed
    assert abs(opp.profit_cents - 29.8) < 0.05
    assert opp.max_units == 250


def test_box_arb_detected():
    # yes ask 45 + no ask 45 = 90 < 100 - fees
    markets = [{"ticker": "M0"}]
    books = {"M0": book("M0", yes_bids=[[55, 60]], no_bids=[[55, 40]])}
    opps = [o for o in scan_event(_event(markets), books) if o.kind == "box"]
    assert len(opps) == 1
    assert opps[0].max_units == 40
    assert opps[0].profit_cents > 5


def test_efficient_book_yields_nothing():
    # tight, fair book: yes 49 bid / 51 ask
    markets = [{"ticker": "M0"}, {"ticker": "M1"}]
    books = {
        "M0": book("M0", yes_bids=[[49, 100]], no_bids=[[49, 100]]),
        "M1": book("M1", yes_bids=[[49, 100]], no_bids=[[49, 100]]),
    }
    assert scan_event(_event(markets), books) == []
