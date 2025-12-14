from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator, field_validator
from typing_extensions import Annotated

from app.orders.models import OrderSide, OrderType, OrderStatus

InstrumentStr = Annotated[str, Field(min_length=12, max_length=12)]
LimitPrice = Annotated[Optional[Decimal], Field(None, decimal_places=2)]
QuantityInt = Annotated[int, Field(gt=0)]


class CreateOrderSchema(BaseModel):
    """Schema for creating an order, used for input validation."""
    type: OrderType
    side: OrderSide
    instrument: InstrumentStr
    limit_price: LimitPrice
    quantity: QuantityInt

    @model_validator(mode="before")
    def main_validator(cls, values: dict) -> dict:
        """Validates input values based on order type."""
        order_type = values.get("type")
        limit_price = values.get("limit_price")

        if order_type == OrderType.MARKET.value:
            cls.validate_market_order(limit_price)

        if order_type == OrderType.LIMIT.value:
            cls.validate_limit_order(limit_price)

        return values

    @staticmethod
    def validate_market_order(limit_price: Optional[Decimal]) -> None:
        """Validates that a market order does not include a limit price."""
        if limit_price is not None:
            raise ValueError(
                "Providing a `limit_price` is prohibited for type `market`")
        if limit_price == 0:
            raise ValueError("`limit_price` cannot be 0 for type `market`")

    @staticmethod
    def validate_limit_order(limit_price: Optional[Decimal]) -> None:
        """Validates that a limit order has a valid limit price."""
        if limit_price is None:
            raise ValueError(
                "Attribute `limit_price` is required for type `limit`")
        if limit_price <= 0:
            raise ValueError(
                "The limit price must be greater than 0 for limit orders.")


class OrderResponseSchema(BaseModel):
    """Schema used to return an order, typically maps from ORM model."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    type: OrderType
    side: OrderSide
    instrument: str
    limit_price: Optional[Decimal]
    quantity: int
    status: OrderStatus

    model_config = {"from_attributes": True}


class OrderListResponseSchema(BaseModel):
    """Schema for listing multiple orders with pagination details."""
    total: int
    orders: List[OrderResponseSchema]
    limit: int
    skip: int


class OrderIdValidator(BaseModel):
    """Validator for ensuring the order ID is a valid UUID."""
    order_id: UUID

    @field_validator('order_id', mode='before')
    def validate_order_id(cls, value):
        """Ensures the provided order ID is a valid UUID string."""
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                raise ValueError("Invalid UUID format")
        return value
