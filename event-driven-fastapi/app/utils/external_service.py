import random
import time

from app.orders.schemas import OrderResponseSchema


class ExternalServiceError(Exception):
    """Exception raised when an external service call fails."""
    pass


def simulate_external_call(
    request_data: OrderResponseSchema,
    failure_rate: float = 0.1,
    delay: float = 0.5
) -> None:
    """
    Simulates an external API call with a configurable failure rate and delay.

    :param request_data: The request data to be sent to the external service.
    :param failure_rate: Probability (0 to 1) of failure occurring (default 10%).
    :param delay: Time (in seconds) to simulate network latency or processing.
    :raises ExternalServiceError: If the simulated call fails.
    """

    if not request_data:
        raise ValueError("Required request data not provided")

    if random.random() < failure_rate:
        raise ExternalServiceError(
            "Failed to communicate with external service. Connection not available.")

    time.sleep(delay)
