import sys
import json
import hashlib

from decimal import Decimal
from enum import Enum


def is_testing() -> bool:
    """Check if the app is running in a test environment."""
    return "pytest" in sys.modules


def custom_default(obj):
    """Custom function to handle Decimal and Enum objects during serialization."""
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_order_key(order_data) -> str:
    """Generate a unique order hash key based on order data."""
    order_json = json.dumps(order_data.model_dump(),
                            sort_keys=True, default=custom_default)
    order_hash = hashlib.sha256(order_json.encode()).hexdigest()
    return f"order:{order_hash}"
