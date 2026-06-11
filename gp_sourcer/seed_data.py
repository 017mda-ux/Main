"""
Seed the signal stores with confirmed data gathered from public sources
(May-June 2026 research session). Run once:  python -m gp_sourcer.seed_data
"""

from __future__ import annotations

from .lp_watch import log_lp_signal
from .pipeline import add_to_pipeline
from .placement_agents import log_offering
from .talent_signals import log_talent_signal


def seed() -> None:
    # --- LP Watch: confirmed commitments from press / disclosures ---
    log_lp_signal("yale", "Bain Capital Funds IX-XIII (secondary sale)", "Bain Capital",
                  source="Project Gatsby reporting", signal_date="2026-05-15",
                  note="Yale selling ~$2.5B of PE positions incl. Bain, Golden Gate, CD&R, Insight, General Catalyst")
    log_lp_signal("swib", "Energy Capital Partners ECP VI", "Energy Capital Partners",
                  source="Dakota May 2026 fund report", signal_date="2026-05-20",
                  note="Among backers tracking toward $4.8B summer close")
    log_lp_signal("cppib", "EQT BPEA Private Equity Fund IX", "EQT / BPEA",
                  commitment_usd=None, source="Press, April 2026", signal_date="2026-04-28",
                  note="Record $15.6B Asia-Pacific close")

    # --- Talent signals: examples illustrating the two signal types ---
    log_talent_signal(
        person="Josh Harris (precedent case)", prior_firm="Apollo Global Management",
        prior_title="Co-Founder", signal_type="spinout", new_firm="26North Partners",
        evidence="Debut PE fund closed at $5.9B, May 2026 — model spinout outcome",
        signal_date="2026-05-10", status="spinout_confirmed")

    # --- Placement agents: example mandate in market ---
    log_offering("pacenote", "TBD — emerging buyout mandate", gp_name="Undisclosed",
                 strategy="buyout", expected_close="Q4 2026",
                 received_date="2026-06-01", status="teaser_received",
                 note="Pacenote focus = spinouts/Fund I — matches emerging-manager target")

    # --- Pipeline: starter cards from the current feed ---
    add_to_pipeline("Hughes Growth Equity Fund II", "Hughes & Company", "growth",
                    fund_number=2, source="form_d", stage="initial_review",
                    conviction="medium", note="Fund II growth, healthcare+software — emerging, in-mandate pending size")
    add_to_pipeline("Crosscourt Ventures II, LP", "Crosscourt", "venture",
                    fund_number=2, source="form_d", stage="radar",
                    note="Early-stage AI/defense — deprioritised unless >$200M; confirm size")
    add_to_pipeline("Benford Capital Partners III UGM CIV-A, L.P.", "Benford Capital Partners",
                    "buyout", fund_number=3, source="form_d", stage="radar",
                    note="Fund III lower-MM buyout — last emerging vintage, confirm size in $200M-1B band")

    print("Seed complete.")


if __name__ == "__main__":
    seed()
