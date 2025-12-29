import time
from functools import wraps


def time_it(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Record the start time
        start_time = time.perf_counter()

        # Execute the actual function
        result = func(*args, **kwargs)

        # Record the end time
        end_time = time.perf_counter()

        # Calculate and log the duration
        duration = end_time - start_time
        print(f"Function '{func.__name__}' executed in {duration:.4f} seconds")

        return result

    return wrapper
