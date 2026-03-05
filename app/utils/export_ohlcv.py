"""
Export OHLCV data to CSV using ccxt.

This utility fetches historical candlestick data from an exchange and writes
it to a CSV file with columns: timestamp, open, high, low, close, volume.

Usage example:
  python utils/export_ohlcv.py --exchange okx --symbol ETH/USDT \
         --timeframe 5m --limit 200 --out docs/samples/ETH-USDT_5m_200.csv

Notes:
- Uses OKX spot market by default (options.defaultType='spot').
- Timestamp is exported in milliseconds (epoch ms) consistent with ccxt.
"""

from __future__ import annotations

from typing import Any, List, Sequence
import argparse
import csv
import os

import ccxt  # type: ignore


def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str, limit: int) -> List[List[Any]]:
    """
    Fetch OHLCV from the given exchange via ccxt.

    :param exchange_id: Exchange id (e.g., 'okx')
    :param symbol: Market symbol (e.g., 'ETH/USDT')
    :param timeframe: Timeframe (e.g., '5m')
    :param limit: Number of bars to fetch
    :return: List of [timestamp(ms), open, high, low, close, volume]
    """
    cls = getattr(ccxt, exchange_id, None)
    if cls is None:
        raise ValueError(f"Unknown exchange id: {exchange_id}")

    exchange = cls(
        {
            "enableRateLimit": True,
            "options": {
                # default to spot; change to 'swap' if needed
                "defaultType": "spot",
            },
        }
    )

    exchange.load_markets()
    if not exchange.has.get("fetchOHLCV", False):
        raise RuntimeError(f"Exchange '{exchange_id}' does not support fetchOHLCV")

    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not isinstance(ohlcv, list) or not ohlcv:
        raise RuntimeError("Received empty OHLCV response")
    return ohlcv


def write_csv(ohlcv: Sequence[Sequence[Any]], out_path: str) -> None:
    """
    Write OHLCV data to CSV.

    :param ohlcv: Sequence of rows [timestamp(ms), open, high, low, close, volume]
    :param out_path: Output CSV path
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for row in ohlcv:
            ts, o, h, low, c, v = row[:6]
            writer.writerow([ts, o, h, low, c, v])


def main() -> None:
    parser = argparse.ArgumentParser(description="Export OHLCV to CSV via ccxt")
    parser.add_argument("--exchange", default="okx", help="Exchange id, e.g. okx")
    parser.add_argument("--symbol", default="ETH/USDT", help="Symbol, e.g. ETH/USDT")
    parser.add_argument("--timeframe", default="5m", help="Timeframe, e.g. 5m")
    parser.add_argument("--limit", type=int, default=200, help="Number of bars to fetch")
    parser.add_argument("--out", default="docs/samples/ETH-USDT_5m_200.csv", help="Output CSV path")
    args = parser.parse_args()

    try:
        data = fetch_ohlcv(args.exchange, args.symbol, args.timeframe, args.limit)
        write_csv(data, args.out)
        print(f"Exported {len(data)} bars to {args.out}")
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise


if __name__ == "__main__":
    main()
