from sqlalchemy.orm import Session
from rq import Queue, Retry

from app.core.database import get_session
from app.core.redis import redis_client
from app.utils.logger import logger_config
from app.utils.external_service import simulate_external_call, ExternalServiceError
from app.orders.models import Order, OrderStatus
from app.orders.schemas import OrderResponseSchema, OrderIdValidator
from app.orders.exceptions import OrderNotFoundError, RedisTaskQueueError


logger = logger_config("app.orders.tasks")


class OrderProcessor:
    """Handles order processing and error handling."""

    def __init__(self, order_task: OrderIdValidator) -> None:
        self.order_id = order_task.order_id
        self.db: Session = next(get_session())
        self.order = None

    def fetch_order(self) -> None:
        """Fetches order and processing task from the database."""
        self.order = self.db.get(Order, self.order_id)

        if self.order is None:
            error_message = f"Order {self.order_id} not found."
            logger.error(error_message)
            raise OrderNotFoundError(error_message)

    def update_status(self, order_status: OrderStatus) -> None:
        """Updates order and task status in the database."""
        if self.order:
            self.order.status = order_status
            self.db.commit()

    def process(self):
        """Main method to process the order."""
        try:
            self.fetch_order()
            logger.info(f"Placing order {self.order_id} in stock exchange.")
            order_data = OrderResponseSchema.model_validate(self.order)

            simulate_external_call(order_data)

            self.update_status(OrderStatus.COMPLETED)
            logger.info(f"Order {self.order_id} marked as COMPLETED.")

        except OrderNotFoundError as e:
            raise e

        except ExternalServiceError as e:
            self.db.rollback()
            self.update_status(OrderStatus.FAILED)
            error_message = (
                f"Order {self.order_id} failed to be placed: {str(e)}")
            logger.error(error_message)
            raise RuntimeError(error_message)

        except Exception as e:
            self.db.rollback()
            self.update_status(OrderStatus.FAILED)
            error_message = (
                f"Critical error processing order {self.order_id}: {str(e)}")
            logger.critical(error_message)
            raise RuntimeError(error_message)

        finally:
            self.db.close()


def process_order_task(order_id: str):
    """Wrapper function to instantiate and run the order processor."""
    processor = OrderProcessor(OrderIdValidator(order_id=order_id))
    processor.process()


def enqueue_order_processing(order_id: str) -> None:
    """Enqueue the task to process the order."""

    try:
        retry_options = Retry(
            max=5,
            interval=10,
        )
        queue = Queue(connection=redis_client)
        job = queue.enqueue(
            process_order_task,
            order_id,
            job_timeout=60,
            result_ttl=5000,
            retry=retry_options
        )

        logger.info(
            f"Job {job.id} enqueued for order {order_id} with retries.")

    except Exception as e:
        error_message = (
            f"Failed to enqueue task for order {order_id}: {str(e)}")
        logger.error(error_message)
        raise RedisTaskQueueError(error_message)
