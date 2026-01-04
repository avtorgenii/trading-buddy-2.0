from dataclasses import asdict, is_dataclass, dataclass
from enum import Enum
from typing import Any
from decimal import Decimal

from bingX.exceptions import OrderException


class DictMixin:
    def to_dict(self) -> dict[str, Any]:
        def convert_value(value):
            # Handle None values
            if value is None:
                return None

            # Handle enums
            if isinstance(value, Enum):
                return value.value

            # Handle Decimal
            if isinstance(value, Decimal):
                return float(value)

            # Handle nested dataclasses - convert to dictionaries (not JSON strings yet)
            if is_dataclass(value):
                return value.to_dict() if hasattr(value, 'to_dict') else asdict(value)

            # Handle lists/tuples containing dataclasses or enums
            if isinstance(value, (list, tuple)):
                return [convert_value(item) for item in value]

            # Handle dictionaries
            if isinstance(value, dict):
                return {k: convert_value(v) for k, v in value.items()}

            # Return the value as-is for basic types
            return value

        # Convert the current dataclass to dict and process each field
        if is_dataclass(self):
            result = {}
            for field_name, field_value in self.__dict__.items():
                if field_value is not None:  # Skip None values
                    result[field_name] = convert_value(field_value)
            return result
        else:
            return convert_value(self)


class MarginType(Enum):
    ISOLATED = "ISOLATED"
    CROSSED = "CROSSED"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRIGGER_LIMIT = "TRIGGER_LIMIT"
    TRIGGER_MARKET = "TRIGGER_MARKET"


class WorkingType(Enum):
    MARK_PRICE = "MARK_PRICE"
    CONTRACT_PRICE = "CONTRACT_PRICE"
    INDEX_PRICE = "INDEX_PRICE"


@dataclass
class StopLossOrder(DictMixin):
    stopPrice: Decimal
    price: Decimal
    type: OrderType = OrderType.STOP_MARKET
    workingType: WorkingType = WorkingType.MARK_PRICE


@dataclass
class TakeProfitOrder(DictMixin):
    stopPrice: Decimal
    price: Decimal
    type: OrderType = OrderType.TAKE_PROFIT_MARKET
    workingType: WorkingType = WorkingType.MARK_PRICE


@dataclass
class Order(DictMixin):
    symbol: str
    side: Side
    positionSide: PositionSide
    takeProfit: TakeProfitOrder | None = None
    stopLoss: StopLossOrder | None = None
    quantity: Decimal | None = None
    type: OrderType = OrderType.MARKET
    price: Decimal | None = None
    stopPrice: Decimal | None = None
    workingType: WorkingType = WorkingType.CONTRACT_PRICE
    recvWindow: int | None = None

    def __post_init__(self):
        if self.type == OrderType.LIMIT:
            if (self.quantity is None) or (self.price is None):
                raise OrderException("LIMIT order must have quantity and price")
        elif self.type == OrderType.MARKET:
            if self.quantity is None:
                raise OrderException("MARKET order must have quantity")
        elif self.type == OrderType.TRIGGER_LIMIT:
            if (self.quantity is None) or (self.stopPrice is None) or (self.price is None):
                raise OrderException("TRIGGER_LIMIT order must have quantity, stop_price and price")
        elif self.type in [OrderType.STOP_MARKET, OrderType.TAKE_PROFIT_MARKET, OrderType.TRIGGER_MARKET]:
            if (self.quantity is None) or (self.stopPrice is None):
                raise OrderException(
                    "STOP_MARKET, TAKE_PROFIT_MARKET and TRIGGER_MARKET orders must have quantity and stop_price")


class IncomeType(Enum):
    TRANSFER = "TRANSFER"
    REALIZED_PNL = "REALIZED_PNL"
    FUNDING_FEE = "FUNDING_FEE"
    TRADING_FEE = "TRADING_FEE"
    INSURANCE_CLEAR = "INSURANCE_CLEAR"
    TRIAL_FUND = "TRIAL_FUND"
    ADL = "ADL"
    SYSTEM_DEDUCTION = "SYSTEM_DEDUCTION"


@dataclass
class ProfitLossFundFlow(DictMixin):
    symbol: str | None = None
    incomeType: IncomeType | None = None
    startTime: int | None = None
    endTime: int | None = None
    limit: int = 100
    recvWindow: int | None = None


@dataclass
class ForceOrder(DictMixin):
    symbol: str | None = None
    autoCloseType: str | None = None
    startTime: int | None = None
    endTime: int | None = None
    limit: int = 50
    recvWindow: int | None = None


@dataclass
class HistoryOrder(DictMixin):
    symbol: str
    orderId: int | None = None
    startTime: int | None = None
    endTime: int | None = None
    limit: int = 500
    timeStamp: int | None = None
    recvWindow: int | None = None


@dataclass
class HistoryPosition(DictMixin):
    """
    Can be used for querying multiple positions via API, but for my own use case will be used to query only single position with according positionId
    Default
    https://bingx-api.github.io/docs/#/en-us/swapV2/trade-api.html#Query%20Position%20History
    """
    symbol: str
    positionId: int
    recvWindow: int | None = None
    startTs: int | None = None
    endTs: int | None = None
