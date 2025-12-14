import enum
import uuid

from sqlalchemy import Column, String, Integer, Enum, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class OrderSide(enum.Enum):
    """Represents the direction of the order: either BUY or SELL."""
    BUY = "buy"
    SELL = "sell"


class OrderType(enum.Enum):
    """Indicates the type of the order: MARKET or LIMIT."""
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(enum.Enum):
    """Describes the current state of the order: pending, completed, or failed."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Order(Base):
    """Represents an order in the trading system."""

    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True,
                default=uuid.uuid4, index=True)
    type = Column(Enum(OrderType))
    side = Column(Enum(OrderSide))
    instrument = Column(String(12))
    limit_price = Column(Numeric(precision=10, scale=2))
    quantity = Column(Integer)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
