class DatabaseServiceError(Exception):
    """Raised for database-related errors."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(self.detail)


class OrderNotFoundError(Exception):
    """Raised when an order is not found."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(self.detail)


class RedisTaskQueueError(Exception):
    """Raised for Redis task queue issues."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(self.detail)
