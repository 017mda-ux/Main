"""Collectors for official and primary-market data.

Every adapter returns `TimeSeries` or plain dicts and records the URL it read,
so each figure on the page can be traced back to the agency that published it.
"""

from .http import HttpError, get, get_json
from . import fred, treasury_fiscal, treasury_rates, bls, stooq, feeds

__all__ = [
    "HttpError", "get", "get_json",
    "fred", "treasury_fiscal", "treasury_rates", "bls", "stooq", "feeds",
]
