#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Binance Futures Testnet Trading Bot.

Usage examples:
    python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
    python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 80000
    python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 75000
    python cli.py account
    python cli.py ping
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from bot import (
    BinanceClient,
    BinanceAPIError,
    OrderManager,
    OrderRequest,
    setup_logging,
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)

# ── Colour helpers (no external deps) ────────────────────────────────────────

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"


def ok(msg: str) -> None:
    print(f"{GREEN}{BOLD}✔  {msg}{RESET}")


def err(msg: str) -> None:
    print(f"{RED}{BOLD}✘  {msg}{RESET}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"{CYAN}ℹ  {msg}{RESET}")


def warn(msg: str) -> None:
    print(f"{YELLOW}⚠  {msg}{RESET}")


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Market buy:
    python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  Limit sell:
    python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 2800

  Stop-Market (bonus):
    python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 75000

  Account info:
    python cli.py account

  Connectivity check:
    python cli.py ping
        """,
    )

    # Global flags
    parser.add_argument(
        "--log-dir",
        default="logs",
        metavar="DIR",
        help="Directory for log files (default: logs/)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help="Binance API key (overrides env var BINANCE_API_KEY)",
    )
    parser.add_argument(
        "--api-secret",
        default=None,
        metavar="SECRET",
        help="Binance API secret (overrides env var BINANCE_API_SECRET)",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # ── place ──────────────────────────────────────────────────────────────
    place_p = subparsers.add_parser("place", help="Place a new order")
    place_p.add_argument(
        "--symbol", required=True, help="Trading pair symbol (e.g. BTCUSDT)"
    )
    place_p.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        help="Order side: BUY or SELL",
    )
    place_p.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        type=str.upper,
        help="Order type: MARKET | LIMIT | STOP_MARKET",
    )
    place_p.add_argument(
        "--quantity",
        required=True,
        type=str,
        help="Order quantity (e.g. 0.001)",
    )
    place_p.add_argument(
        "--price",
        default=None,
        type=str,
        help="Limit price (required for LIMIT orders)",
    )
    place_p.add_argument(
        "--stop-price",
        default=None,
        type=str,
        dest="stop_price",
        help="Stop price (required for STOP_MARKET orders)",
    )
    place_p.add_argument(
        "--tif",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time-in-force for LIMIT orders (default: GTC)",
    )

    # ── account ────────────────────────────────────────────────────────────
    subparsers.add_parser("account", help="Display futures account summary")

    # ── ping ───────────────────────────────────────────────────────────────
    subparsers.add_parser("ping", help="Check connectivity to Binance Futures Testnet")

    return parser


# ── Command handlers ──────────────────────────────────────────────────────────

def cmd_ping(client: BinanceClient) -> None:
    info("Pinging Binance Futures Testnet…")
    alive = client.ping()
    if alive:
        ok("Testnet is reachable.")
    else:
        err("Could not reach testnet.")
        sys.exit(1)


def cmd_account(client: BinanceClient) -> None:
    info("Fetching account information…")
    try:
        data = client.get_account_info()
    except BinanceAPIError as exc:
        err(f"API error {exc.code}: {exc.message}")
        sys.exit(1)
    except Exception as exc:
        err(f"Unexpected error: {exc}")
        sys.exit(1)

    total_wallet = data.get("totalWalletBalance", "N/A")
    avail_balance = data.get("availableBalance", "N/A")
    unrealised_pnl = data.get("totalUnrealizedProfit", "N/A")
    positions = [p for p in data.get("positions", []) if float(p.get("positionAmt", 0)) != 0]

    print()
    print(f"{BOLD}{'─'*45}{RESET}")
    print(f"{BOLD}  Futures Account Summary (Testnet){RESET}")
    print(f"{'─'*45}")
    print(f"  Wallet Balance    : {CYAN}{total_wallet} USDT{RESET}")
    print(f"  Available Balance : {CYAN}{avail_balance} USDT{RESET}")
    print(f"  Unrealised PnL    : {CYAN}{unrealised_pnl} USDT{RESET}")
    print(f"{'─'*45}")

    if positions:
        print(f"{BOLD}  Open Positions:{RESET}")
        for pos in positions:
            symbol = pos.get("symbol", "")
            amt = pos.get("positionAmt", "0")
            entry = pos.get("entryPrice", "0")
            upnl = pos.get("unrealizedProfit", "0")
            print(f"    {symbol:12s} amt={amt:>12s}  entry={entry:>12s}  uPnL={upnl}")
    else:
        print("  No open positions.")
    print(f"{'─'*45}")


def cmd_place(args: argparse.Namespace, client: BinanceClient) -> None:
    # ── Validation ──────────────────────────────────────────────────────────
    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity = validate_quantity(args.quantity)
        price = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValueError as exc:
        err(f"Validation error: {exc}")
        sys.exit(1)

    # ── Build request ────────────────────────────────────────────────────────
    req = OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=args.tif,
    )

    print()
    print(req.to_display())
    print()

    # ── Submit ───────────────────────────────────────────────────────────────
    manager = OrderManager(client)
    try:
        response = manager.place_order(req)
    except BinanceAPIError as exc:
        err(f"Order failed — API error {exc.code}: {exc.message}")
        sys.exit(1)
    except Exception as exc:
        err(f"Order failed — {exc}")
        sys.exit(1)

    print(response.to_display())
    print()
    ok(f"Order placed successfully! Order ID: {response.order_id}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args()

    logger = setup_logging(log_dir=args.log_dir)

    # Resolve credentials: CLI flag > env var
    api_key = args.api_key or os.getenv("BINANCE_API_KEY", "")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        err(
            "API credentials not found.\n"
            "   Set BINANCE_API_KEY and BINANCE_API_SECRET in your .env file,\n"
            "   or pass --api-key and --api-secret flags."
        )
        sys.exit(1)

    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        err(str(exc))
        sys.exit(1)

    if args.command == "ping":
        cmd_ping(client)
    elif args.command == "account":
        cmd_account(client)
    elif args.command == "place":
        cmd_place(args, client)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
