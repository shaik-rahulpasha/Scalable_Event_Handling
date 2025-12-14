import pytest

from typing import Any
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.orders.models import Order, OrderSide, OrderStatus, OrderType


class TestOrderCreationWithBackgroundTask:
    """Test order creation and background task handling."""

    @pytest.fixture
    def mock_task_processing(self, mocker: MagicMock) -> Any:
        """Mock background task processing."""
        return mocker.patch(
            "app.orders.routers.enqueue_order_processing"
        )

    @pytest.fixture
    def mock_redis_exists(self, mocker: MagicMock) -> Any:
        """Mock redis_client.exists method."""
        return mocker.patch("app.orders.routers.redis_client.exists")

    @pytest.fixture
    def mock_redis_set(self, mocker: MagicMock) -> Any:
        """Mock redis_client.exists method."""
        return mocker.patch("app.orders.routers.redis_client.setex")

    def test_create_limit_order(
        self,
        db_session: Session,
        client: TestClient,
        mock_redis_set: MagicMock,
        mock_task_processing: MagicMock
    ) -> None:
        """Test creating a limit order."""
        response = client.post(
            "/orders",
            json={
                "type": "limit",
                "side": "sell",
                "instrument": "stringstring",
                "limit_price": 150,
                "quantity": 100,
            },
        )

        assert response.status_code == 201
        response_data = response.json()

        assert response_data["type"] == "limit"
        assert response_data["side"] == "sell"
        assert response_data["instrument"] == "stringstring"
        assert response_data["limit_price"] == "150.00"
        assert response_data["quantity"] == 100
        assert response_data["status"] == "pending"

        order_in_db = db_session.get(Order, response_data["id"])

        assert order_in_db is not None
        assert order_in_db.type == OrderType.LIMIT
        assert order_in_db.side == OrderSide.SELL
        assert order_in_db.instrument == "stringstring"
        assert order_in_db.limit_price == Decimal(150.00)
        assert order_in_db.quantity == 100
        assert order_in_db.status == OrderStatus.PENDING

        mock_task_processing.assert_called_once()

    def test_create_market_order(
        self,
        client: TestClient,
        mock_task_processing: MagicMock,
        mock_redis_set: MagicMock,
        db_session: Session
    ) -> None:
        """Test creating a market order."""
        response = client.post(
            "/orders",
            json={
                "type": "market",
                "side": "buy",
                "instrument": "stringstring",
                "quantity": 10,
            },
        )

        assert response.status_code == 201
        response_data = response.json()

        assert response_data["type"] == "market"
        assert response_data["side"] == "buy"
        assert response_data["instrument"] == "stringstring"
        assert response_data["quantity"] == 10
        assert response_data["status"] == "pending"

        order_in_db = db_session.get(Order, response_data["id"])

        assert order_in_db is not None
        assert order_in_db.type == OrderType.MARKET
        assert order_in_db.side == OrderSide.BUY
        assert order_in_db.instrument == "stringstring"
        assert order_in_db.quantity == 10
        assert order_in_db.status == OrderStatus.PENDING

        mock_task_processing.assert_called_once()

    def test_create_order_with_duplicate_redis_key(
        self, client: TestClient, mock_redis_exists: MagicMock
    ) -> None:
        """Test creating an order with an existing Redis key."""
        mock_redis_exists.return_value = True

        response = client.post(
            "/orders",
            json={
                "type": "limit",
                "side": "sell",
                "instrument": "stringstring",
                "limit_price": 150.00,
                "quantity": 100,
            },
        )

        assert response.status_code == 409
        response_data = response.json()

        assert response_data["detail"] == (
            "Duplicate order detected. Please wait before retrying."
        )


class TestOrderValidation:
    """Tests for order creation validation."""

    @pytest.mark.parametrize(
        "order_data, expected_status_code, expected_error_msg",
        [
            # Limit order without limit_price
            (
                {
                    "type": "limit",
                    "side": "sell",
                    "instrument": "stringstring",
                    "quantity": 100,
                },
                422,
                "Value error, Attribute `limit_price` is required for type `limit`",
            ),
            # Market order with limit price
            (
                {
                    "type": "market",
                    "side": "buy",
                    "instrument": "stringstring",
                    "limit_price": 150.00,
                    "quantity": 100,
                },
                422,
                "Value error, Providing a `limit_price` is prohibited for type `market`",
            ),
            # Limit order with invalid limit price
            (
                {
                    "type": "limit",
                    "side": "sell",
                    "instrument": "stringstring",
                    "limit_price": -150.00,
                    "quantity": 100,
                },
                422,
                "Value error, The limit price must be greater than 0 for limit orders.",
            ),
            # Invalid side
            (
                {
                    "type": "limit",
                    "side": "invalid_side",
                    "instrument": "stringstring",
                    "limit_price": 150.00,
                    "quantity": 100,
                },
                422,
                "Input should be 'buy' or 'sell'",
            ),
            # Invalid instrument length
            (
                {
                    "type": "limit",
                    "side": "buy",
                    "instrument": "short",
                    "limit_price": 150.00,
                    "quantity": 100,
                },
                422,
                "String should have at least 12 characters",
            ),
        ],
    )
    def test_order_validation(
        self, client: TestClient, order_data, expected_status_code, expected_error_msg
    ):
        """Test order creation with various invalid payloads."""
        response = client.post("/orders", json=order_data)

        assert response.status_code == expected_status_code
        response_data = response.json()

        assert expected_error_msg in response_data["detail"][0]["msg"]
