"""
trading_bot.bot — Binance Futures Testnet trading bot package.
"""

from .client import BinanceClient, BinanceAPIError
from .orders import OrderManager, OrderRequest, OrderResponse
from .validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)
from .logging_config import setup_logging

__all__ = [
    "BinanceClient",
    "BinanceAPIError",
    "OrderManager",
    "OrderRequest",
    "OrderResponse",
    "validate_symbol",
    "validate_side",
    "validate_order_type",
    "validate_quantity",
    "validate_price",
    "validate_stop_price",
    "setup_logging",
]
