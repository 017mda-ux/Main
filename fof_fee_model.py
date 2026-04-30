"""
Fund of Funds Fee Structure Model — Option 1
---------------------------------------------
Assumptions:
  - Committed capital normalized to $1.00
  - Fund life: 10 years
  - Mgmt fee: 1.5% p.a. on committed capital → $0.15 total drag
  - Invested capital: $0.85 (committed minus mgmt fees)
  - Placement fee: 10% of gross profit (on portfolio, no hurdle) — normalized out before carry
  - DPI threshold: 3x on paid-in (committed) capital = $3.00 in LP distributions

Waterfall (on net proceeds after mgmt fees + placement):
  Pre-3x DPI    → 90/10 LP/GP from dollar one (no preferred return)
  3x DPI catch-up → 100% GP until GP has received 15% of total net profit
  Post catch-up  → 85/15 LP/GP
"""

from dataclasses import dataclass
from typing import Tuple
import sys

# ── Model parameters ──────────────────────────────────────────────────────────
COMMITTED       = 1.00
MGMT_FEE_TOTAL  = 0.15          # 1.5% × 10yr
INVESTED        = COMMITTED - MGMT_FEE_TOTAL   # 0.85
PLACEMENT_RATE  = 0.10          # 10% of gross portfolio profit, no hurdle
DPI_THRESHOLD   = 3.00          # 3x DPI in LP distributions (on committed)

# Carry tiers
PRE_DPI_LP      = 0.90          # LP share pre-3x DPI
PRE_DPI_GP      = 0.10
POST_CATCHUP_LP = 0.85          # LP share after catch-up
POST_CATCHUP_GP = 0.15
TARGET_GP_CARRY = 0.15          # GP target carry rate (15% of total net profit)


@dataclass
class WaterfallResult:
    gross_moic_invested:   float   # gross MOIC on invested capital
    gross_moic_committed:  float   # gross MOIC on committed capital
    gross_proceeds:        float   # raw portfolio proceeds per $1 committed
    mgmt_fees:             float
    placement_fee:         float
    net_to_waterfall:      float   # gross_proceeds - placement_fee (mgmt already out)
    net_profit:            float   # net_to_waterfall - committed capital returned
    lp_capital_returned:   float
    lp_profit:             float
    gp_carry:              float
    lp_total:              float   # capital + profit
    net_moic_lp:           float   # on committed capital
    fee_drag:              float   # gross_committed - net_moic_lp
    effective_fee_pct:     float   # total fees as % of gross profit
    regime:                str


def waterfall(gross_moic_invested: float) -> WaterfallResult:
    """Compute full waterfall for a given gross MOIC on invested capital."""
    Gi = gross_moic_invested
    Gc = Gi * INVESTED   # gross MOIC on committed capital

    gross_proceeds = Gi * INVESTED  # = Gc × committed = Gc

    # Placement fee: 10% of gross portfolio PROFIT (no hurdle)
    gross_portfolio_profit = max(0.0, (Gi - 1.0) * INVESTED)
    placement_fee = PLACEMENT_RATE * gross_portfolio_profit

    # Net proceeds entering the waterfall (management fees already consumed)
    net_to_waterfall = gross_proceeds - placement_fee

    # Return of committed capital to LP (LP paid in $1.00, including mgmt fees)
    capital_to_return = COMMITTED  # $1.00

    if net_to_waterfall <= capital_to_return:
        # Loss scenario — LP gets everything, no carry
        lp_capital_returned = net_to_waterfall
        lp_profit = 0.0
        gp_carry  = 0.0
        regime = "Loss"
    else:
        lp_capital_returned = capital_to_return
        net_profit = net_to_waterfall - capital_to_return  # profit pool for carry split

        lp_profit, gp_carry, regime = _carry_waterfall(net_profit)

    lp_total = lp_capital_returned + lp_profit
    net_moic_lp = lp_total / COMMITTED

    gross_profit_committed = max(0.0, Gc - 1.0)
    total_fees = Gc - net_moic_lp
    effective_fee_pct = (total_fees / gross_profit_committed * 100) if gross_profit_committed > 0 else 0.0

    return WaterfallResult(
        gross_moic_invested   = Gi,
        gross_moic_committed  = Gc,
        gross_proceeds        = gross_proceeds,
        mgmt_fees             = MGMT_FEE_TOTAL,
        placement_fee         = placement_fee,
        net_to_waterfall      = net_to_waterfall,
        net_profit            = net_to_waterfall - min(net_to_waterfall, capital_to_return),
        lp_capital_returned   = lp_capital_returned,
        lp_profit             = lp_profit,
        gp_carry              = gp_carry,
        lp_total              = lp_total,
        net_moic_lp           = net_moic_lp,
        fee_drag              = Gc - net_moic_lp,
        effective_fee_pct     = effective_fee_pct,
        regime                = regime,
    )


def _carry_waterfall(net_profit: float) -> Tuple[float, float, str]:
    """
    Split net_profit (after capital return) between LP and GP.

    LP distributions at 3x DPI = $3.00 total → LP profit portion = $3.00 - $1.00 = $2.00.
    Pre-DPI: 90/10 → LP gets 90% of profits. So profits needed for LP to hit $2.00 = 2.00/0.90 = $2.222...
    Catch-up: 100% GP until GP total carry = 15% × total_net_profit.
    GP catch-up needed = 15%×T - 10%×2.222 = 0.15T - 0.2222
    Catch-up complete when remaining profit > catch-up needed.
    """
    T = net_profit

    # ─ Pre-3x DPI threshold ─
    # LP profit portion to reach 3x DPI: PRE_DPI_LP × pre_dpi_profit = 2.00 → pre_dpi_profit = 2.222...
    lp_profit_for_3x_dpi = DPI_THRESHOLD - COMMITTED   # $2.00 per $1 committed
    pre_dpi_profit_pool  = lp_profit_for_3x_dpi / PRE_DPI_LP   # $2.2222...

    if T <= pre_dpi_profit_pool:
        # Never hits 3x DPI — pure 90/10
        lp_profit = PRE_DPI_LP * T
        gp_carry  = PRE_DPI_GP * T
        regime = f"Pre-3x DPI (90/10)"
    else:
        # Stage 1: pre-DPI
        lp_stage1 = PRE_DPI_LP * pre_dpi_profit_pool   # = $2.00 exactly
        gp_stage1 = PRE_DPI_GP * pre_dpi_profit_pool   # = $0.2222...

        remaining = T - pre_dpi_profit_pool

        # Stage 2: catch-up — GP needs to reach TARGET_GP_CARRY × T total
        gp_target_total = TARGET_GP_CARRY * T
        gp_catchup_needed = max(0.0, gp_target_total - gp_stage1)

        if remaining <= gp_catchup_needed:
            # Catch-up not complete — all remaining to GP
            lp_profit = lp_stage1
            gp_carry  = gp_stage1 + remaining
            regime = "Catch-up (in progress)"
        else:
            # Stage 3: post catch-up — 85/15
            post_catchup_pool = remaining - gp_catchup_needed
            lp_profit = lp_stage1 + POST_CATCHUP_LP * post_catchup_pool
            gp_carry  = gp_stage1 + gp_catchup_needed + POST_CATCHUP_GP * post_catchup_pool
            regime = "Post catch-up (85/15)"

    return lp_profit, gp_carry, regime


def print_table(scenarios_gc: list[float]) -> None:
    """Print formatted waterfall table for a list of gross MOICs on committed capital."""
    # Convert gross-on-committed to gross-on-invested
    scenarios = [gc / INVESTED for gc in scenarios_gc]

    hdr = (
        f"{'Gross (inv)':>11} │ {'Gross (com)':>11} │ {'Net LP':>8} │ "
        f"{'Mgmt Fee':>9} │ {'Placement':>10} │ {'GP Carry':>9} │ "
        f"{'Fee Drag':>9} │ {'Eff. Fee%':>9} │ Regime"
    )
    sep = "─" * len(hdr)

    print()
    print("FUND OF FUNDS FEE MODEL — OPTION 1")
    print("=" * len(hdr))
    print(f"  Committed capital: $1.00  │  Mgmt fee: 1.5% × 10yr = $0.15  │  Invested: $0.85")
    print(f"  Placement fee: 10% of gross portfolio profit (no hurdle)")
    print(f"  Carry: Pre-3x DPI → 90/10  │  3x catch-up → 100% GP (to 15%)  │  Post → 85/15")
    print("=" * len(hdr))
    print(hdr)
    print(sep)

    for Gi in scenarios:
        r = waterfall(Gi)
        flag = " ◄" if abs(r.gross_moic_committed - 3.48) < 0.08 or abs(r.gross_moic_committed - 3.63) < 0.08 else ""
        print(
            f"{r.gross_moic_invested:>10.2f}x │ {r.gross_moic_committed:>10.2f}x │ "
            f"{r.net_moic_lp:>7.2f}x │ "
            f"${r.mgmt_fees:>7.3f}  │ ${r.placement_fee:>8.3f}  │ ${r.gp_carry:>7.3f}  │ "
            f"${r.fee_drag:>7.3f}  │ {r.effective_fee_pct:>8.1f}% │ {r.regime}{flag}"
        )

    print(sep)
    print()
    print("  Gross (inv)  = MOIC on invested capital ($0.85 per $1 committed)")
    print("  Gross (com)  = MOIC on committed capital (investor perspective)")
    print("  Net LP       = Net MOIC to LP on committed capital (after all fees)")
    print("  Eff. Fee%    = Total fees (mgmt + placement + carry) as % of gross profit")
    print("  ◄            = DPI catch-up zone (3x → 3.63x gross on committed)")
    print()


def print_fee_breakdown(scenarios_gc: list[float]) -> None:
    """Print fee composition breakdown."""
    scenarios = [gc / INVESTED for gc in scenarios_gc]

    print("FEE COMPOSITION BREAKDOWN (per $1 committed)")
    print("-" * 90)
    hdr2 = f"{'Gross (com)':>11} │ {'Mgmt':>7} │ {'Placement':>10} │ {'GP Carry':>9} │ {'Total Fees':>11} │ {'LP Net':>8} │ {'LP%':>6}"
    print(hdr2)
    print("-" * 90)
    for Gi in scenarios:
        r = waterfall(Gi)
        total_fees = r.mgmt_fees + r.placement_fee + r.gp_carry
        lp_pct = r.net_moic_lp / r.gross_moic_committed * 100 if r.gross_moic_committed > 0 else 0
        print(
            f"{r.gross_moic_committed:>10.2f}x │ "
            f"${r.mgmt_fees:>5.3f}  │ ${r.placement_fee:>8.3f}  │ ${r.gp_carry:>7.3f}  │ "
            f"${total_fees:>9.3f}  │ {r.net_moic_lp:>7.2f}x │ {lp_pct:>5.1f}%"
        )
    print("-" * 90)
    print()


def print_dollar_table(fund_size_m: float, gross_multiples: list[int]) -> None:
    """
    Print a clean dollar-value table for a given fund size (in $M)
    at integer gross MOIC increments (on committed capital).
    """
    scale = fund_size_m  # multiply normalized $1 figures by this

    invested_m  = INVESTED * scale
    mgmt_fee_m  = MGMT_FEE_TOTAL * scale

    col_w = 11  # column width for dollar figures

    title = f"OPTION 1 — ${fund_size_m:.0f}M FUND  |  Gross on committed capital"
    print()
    print("=" * 85)
    print(f"  {title}")
    print(f"  Committed: ${fund_size_m:.0f}M  |  Invested: ${invested_m:.1f}M  |  Mgmt fees: ${mgmt_fee_m:.1f}M (1.5% × 10yr)")
    print(f"  Placement: 10% of gross profit, no hurdle")
    print(f"  Carry: 90/10 pre-3x DPI  →  100% GP catch-up to 15%  →  85/15")
    print("=" * 85)

    hdr = (
        f"  {'Gross':>6}  {'Net':>6}  │  "
        f"{'Mgmt Fee':>{col_w}}  {'Placement':>{col_w}}  {'GP Carry':>{col_w}}  {'Total Fees':>{col_w}}  │  Regime"
    )
    sep = "  " + "─" * 83
    print(hdr)
    print(sep)

    for gc in gross_multiples:
        r = waterfall(gc / INVESTED)

        mgmt_m      = r.mgmt_fees      * scale
        placement_m = r.placement_fee  * scale
        carry_m     = r.gp_carry       * scale
        total_fee_m = (r.mgmt_fees + r.placement_fee + r.gp_carry) * scale

        # Flag the catch-up dead zone (in-progress only, not post)
        flag = "  ◄ GP catch-up" if r.regime == "Catch-up (in progress)" else ""

        print(
            f"  {r.gross_moic_committed:>5.1f}x  {r.net_moic_lp:>5.2f}x  │  "
            f"${mgmt_m:>{col_w-1}.1f}M  ${placement_m:>{col_w-1}.1f}M  ${carry_m:>{col_w-1}.1f}M  ${total_fee_m:>{col_w-1}.1f}M  │  {r.regime}{flag}"
        )

    print(sep)
    print(f"  {'Gross':>6}  {'Net':>6}  │  {'Mgmt Fee':>{col_w}}  {'Placement':>{col_w}}  {'GP Carry':>{col_w}}  {'Total Fees':>{col_w}}")
    print()
    print("  Gross     = MOIC on committed capital (before all fees)")
    print("  Net       = MOIC to LP on committed capital (after mgmt + placement + carry)")
    print("  Placement = 10% of gross profit paid to underlying managers (no hurdle)")
    print("  GP Carry  = incentive fee retained by FoF manager per waterfall")
    print("  Total     = Mgmt + Placement + GP Carry")
    print()
    print("  Note: GP catch-up zone falls between 3x and 4x gross (~3.5x–3.6x).")
    print("        LP net is flat at $90.0M / 3.00x during that band.")
    print()
    print()


if __name__ == "__main__":
    print_dollar_table(
        fund_size_m    = 30,
        gross_multiples = list(range(1, 8)),   # 1x through 7x
    )
