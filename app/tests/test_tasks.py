import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.orders.models import Order, OrderType, OrderSide, OrderStatus
from app.orders.tasks import process_order_task
from app.utils.external_service import ExternalServiceError
from app.orders.exceptions import OrderNotFoundError


class TestOrderProcessor:
    """Tests for processing orders."""

    @pytest.fixture
    def mock_simulate_external_call(self, mocker: MagicMock) -> MagicMock:
        """Mock external order placement failure."""
        return mocker.patch(
            "app.orders.tasks.simulate_external_call",
            side_effect=ExternalServiceError(
                "Failed to place order at stock exchange. Connection not available"
            ),
        )

    @pytest.fixture
    def create_test_order(self, db_session: Session) -> callable:
        """Create and return a test order."""
        def _create_order(order_data: dict) -> Order:
            order = Order(**order_data)
            db_session.add(order)
            db_session.commit()
            return order

        return _create_order

    def test_process_order_success(
            self,
            client,
            create_test_order,
            db_session
    ):
        """Test successful order processing."""
        order_data = {
            "instrument": "AAPL",
            "quantity": 100,
            "type": OrderType.LIMIT,
            "side": OrderSide.BUY,
            "limit_price": 150.00,
        }

        test_order = create_test_order(order_data)

        assert test_order.status == OrderStatus.PENDING
        process_order_task(order_id=test_order.id)
        db_session.refresh(test_order)

        assert test_order.status == OrderStatus.COMPLETED

    def test_process_order_error_third_party(
        self,
        client,
        create_test_order,
        db_session,
        mock_simulate_external_call
    ):
        """Test order failure due to third-party service error."""
        order_data = {
            "instrument": "AAPL",
            "quantity": 100,
            "type": OrderType.LIMIT,
            "side": OrderSide.BUY,
            "limit_price": 150.00,
        }

        test_order = create_test_order(order_data)
        assert test_order.status == OrderStatus.PENDING

        with pytest.raises(
            RuntimeError,
            match="Failed to place order at stock exchange. Connection not available"
        ):
            process_order_task(test_order.id)

        db_session.refresh(test_order)
        assert test_order.status == OrderStatus.FAILED

    def test_process_order_not_found(self):
        """Test invalid order ID handling."""
        invalid_order_id = "not_found_order_id"

        with pytest.raises(ValidationError, match="Value error, Invalid UUID format"):
            process_order_task(order_id=invalid_order_id)

        invalid_uuid = str(uuid.uuid4())

        with pytest.raises(OrderNotFoundError, match="not found."):
            process_order_task(order_id=invalid_uuid)
