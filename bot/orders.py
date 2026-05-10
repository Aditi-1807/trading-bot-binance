"""
Order placement logic for Binance Futures Testnet.
Supports MARKET, LIMIT, and STOP_MARKET (bonus) order types.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .client import BinanceClient, BinanceAPIError

logger = logging.getLogger("trading_bot.orders")


@dataclass
class OrderRequest:
    """Validated, structured representation of an order before submission."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    time_in_force: str = "GTC"

    def to_display(self) -> str:
        lines = [
            "┌─ Order Request ─────────────────────────",
            f"│  Symbol     : {self.symbol}",
            f"│  Side       : {self.side}",
            f"│  Type       : {self.order_type}",
            f"│  Quantity   : {self.quantity}",
        ]
        if self.price is not None:
            lines.append(f"│  Price      : {self.price}")
        if self.stop_price is not None:
            lines.append(f"│  Stop Price : {self.stop_price}")
        if self.order_type == "LIMIT":
            lines.append(f"│  TIF        : {self.time_in_force}")
        lines.append("└─────────────────────────────────────────")
        return "\n".join(lines)


@dataclass
class OrderResponse:
    """Parsed response from Binance after order placement."""

    order_id: int
    symbol: str
    status: str
    side: str
    order_type: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    price: str
    raw: dict[str, Any]

    def to_display(self) -> str:
        lines = [
            "┌─ Order Response ────────────────────────",
            f"│  Order ID    : {self.order_id}",
            f"│  Symbol      : {self.symbol}",
            f"│  Status      : {self.status}",
            f"│  Side        : {self.side}",
            f"│  Type        : {self.order_type}",
            f"│  Orig Qty    : {self.orig_qty}",
            f"│  Executed Qty: {self.executed_qty}",
            f"│  Avg Price   : {self.avg_price}",
            f"│  Price       : {self.price}",
            "└─────────────────────────────────────────",
        ]
        return "\n".join(lines)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "OrderResponse":
        return cls(
            order_id=data.get("orderId", 0),
            symbol=data.get("symbol", ""),
            status=data.get("status", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            orig_qty=data.get("origQty", "0"),
            executed_qty=data.get("executedQty", "0"),
            avg_price=data.get("avgPrice", "0"),
            price=data.get("price", "0"),
            raw=data,
        )


class OrderManager:
    """
    Handles construction and submission of futures orders.
    Wraps BinanceClient and provides a clean interface per order type.
    """

    ORDER_ENDPOINT = "/fapi/v1/order"

    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_params(self, req: OrderRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": req.symbol,
            "side": req.side,
            "type": req.order_type,
            "quantity": str(req.quantity),
        }
        if req.order_type == "LIMIT":
            params["price"] = str(req.price)
            params["timeInForce"] = req.time_in_force
        elif req.order_type == "STOP_MARKET":
            params["stopPrice"] = str(req.stop_price)
        return params

    def _submit(self, req: OrderRequest) -> OrderResponse:
        params = self._build_params(req)
        logger.info(
            "Submitting %s %s order | symbol=%s qty=%s price=%s",
            req.side,
            req.order_type,
            req.symbol,
            req.quantity,
            req.price or req.stop_price or "market",
        )
        try:
            raw = self._client.post(self.ORDER_ENDPOINT, params=params)
        except BinanceAPIError as exc:
            logger.error("Order placement failed — API error %s: %s", exc.code, exc.message)
            raise
        except Exception as exc:
            logger.error("Order placement failed — unexpected error: %s", exc)
            raise

        resp = OrderResponse.from_api(raw)
        logger.info(
            "Order accepted | orderId=%s status=%s executedQty=%s avgPrice=%s",
            resp.order_id,
            resp.status,
            resp.executed_qty,
            resp.avg_price,
        )
        return resp

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def place_market_order(
        self, symbol: str, side: str, quantity: Decimal
    ) -> OrderResponse:
        req = OrderRequest(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=quantity,
        )
        return self._submit(req)

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        time_in_force: str = "GTC",
    ) -> OrderResponse:
        req = OrderRequest(
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
        )
        return self._submit(req)

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        stop_price: Decimal,
    ) -> OrderResponse:
        """Bonus: Stop-Market order (closes position at market when stop triggers)."""
        req = OrderRequest(
            symbol=symbol,
            side=side,
            order_type="STOP_MARKET",
            quantity=quantity,
            stop_price=stop_price,
        )
        return self._submit(req)

    def place_order(self, req: OrderRequest) -> OrderResponse:
        """Generic dispatcher — accepts any OrderRequest."""
        return self._submit(req)
