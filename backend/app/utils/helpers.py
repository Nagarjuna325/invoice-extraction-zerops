import time
from datetime import datetime


def get_file_size_mb(size_bytes: int) -> float:
    """Convert bytes to MB"""
    return round(size_bytes / (1024 * 1024), 2)


def get_timestamp() -> str:
    """Get current timestamp as string"""
    return datetime.now().isoformat()


def measure_time(func):
    """Decorator to measure function execution time"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        duration_ms = int((end - start) * 1000)
        return result, duration_ms
    return wrapper