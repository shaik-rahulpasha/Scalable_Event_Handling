from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.redis import redis_client
from app.core.database import get_session
from app.utils.logger import logger_config
from app.orders.schemas import (
    CreateOrderSchema, OrderResponseSchema, OrderListResponseSchema)
from app.orders.services import OrderService
from app.orders.tasks import enqueue_order_processing
from app.utils.common import generate_order_key

logger = logger_config("app.orders.routers")


router = APIRouter()

SECONDS_BEFORE_ALLOWED = 5


@router.post("", response_model=OrderResponseSchema, status_code=201)
def create_order_endpoint(
    order_data: CreateOrderSchema,
    db: Session = Depends(get_session)
):
    """API endpoint to create an order."""

    order_key = generate_order_key(order_data)

    if redis_client.exists(order_key):
        logger.warning(
            f"Duplicate order detected for {order_data.instrument}.")
        raise HTTPException(
            status_code=409,
            detail="Duplicate order detected. Please wait before retrying."
        )

    try:
        logger.info(
            f"Processing order for {order_data.instrument}. Setting Redis lock."
        )
        redis_client.setex(order_key, SECONDS_BEFORE_ALLOWED, "processing")

        order = OrderService.create_order(db, order_data)

        logger.info(
            f"Order created successfully with ID {order.id}. "
            "Enqueueing background task for processing."
        )

        enqueue_order_processing(order_id=order.id)

        return order
    except Exception as e:
        error_message = (
            f"Internal server error while placing the order: {str(e)}")
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)


@router.get("", response_model=OrderListResponseSchema)
def get_orders(
    skip: int = 0, limit: int = 10, db: Session = Depends(get_session)
):
    try:
        orders = OrderService.list_orders(db=db, limit=limit, skip=skip)
        return orders
    except Exception as e:
        error_message = (
            f"Internal server error while fetching saved orders: {str(e)}")
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=(error_message))
