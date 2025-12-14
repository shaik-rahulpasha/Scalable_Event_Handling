from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.orders.schemas import CreateOrderSchema, OrderResponseSchema
from app.orders.models import Order
from app.orders.exceptions import DatabaseServiceError
from app.utils.logger import logger_config

logger = logger_config("app.orders.services")


class OrderService:
    """Handles business logic for order creation and retrieval."""

    @staticmethod
    def create_order(db: Session, order_data: CreateOrderSchema) -> OrderResponseSchema:
        """Create an order and return the response schema."""
        try:
            logger.info(f"Creating order with data: {order_data}")
            order = Order(
                type=order_data.type,
                side=order_data.side,
                instrument=order_data.instrument,
                limit_price=order_data.limit_price,
                quantity=order_data.quantity,
            )
            db.add(order)
            db.commit()

            logger.info(f"Order {order.id} created successfully.")
            return OrderResponseSchema.model_validate(order)

        except (IntegrityError, OperationalError) as e:
            db.rollback()
            error_message = f"Database error occurred: {str(e)}"
            logger.error(error_message)
            raise DatabaseServiceError(detail=error_message)

        except Exception as e:
            db.rollback()
            error_message = f"Unexpected error occurred: {str(e)}"
            logger.error(error_message)
            raise DatabaseServiceError(detail=error_message)

    @staticmethod
    def list_orders(db: Session, limit: int = 10, skip: int = 0) -> dict:
        """List orders with pagination."""
        try:
            total_orders = db.query(Order).count()
            orders = db.query(Order).offset(skip).limit(limit).all()
            order_schemas = [OrderResponseSchema.model_validate(
                order) for order in orders]

            logger.info(f"Fetched {len(orders)} orders out of {total_orders}.")
            return {
                "total": total_orders,
                "orders": order_schemas,
                "limit": limit,
                "skip": skip,
            }
        except Exception as e:
            error_message = f"Error occurred while retrieving orders: {str(e)}"
            logger.error(error_message)
            raise DatabaseServiceError(detail=error_message)
