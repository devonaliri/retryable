# retryable

Lightweight Python decorator library for configurable retry logic with backoff strategies.

## Installation

```bash
pip install retryable
```

## Usage

```python
from retryable import retry

# Retry up to 3 times with exponential backoff
@retry(attempts=3, backoff="exponential", delay=1.0)
def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# Retry on specific exceptions with a fixed delay
@retry(attempts=5, delay=2.0, exceptions=(ConnectionError, TimeoutError))
def connect_to_service():
    return service.connect()
```

### Configuration Options

| Parameter    | Default       | Description                                      |
|--------------|---------------|--------------------------------------------------|
| `attempts`   | `3`           | Maximum number of retry attempts                 |
| `delay`      | `1.0`         | Initial delay in seconds between retries         |
| `backoff`    | `"fixed"`     | Backoff strategy: `fixed`, `exponential`, `linear` |
| `exceptions` | `(Exception,)`| Tuple of exception types that trigger a retry    |
| `on_retry`   | `None`        | Optional callback invoked before each retry      |

### Backoff Strategies

- **fixed** – waits the same `delay` between every attempt
- **linear** – increases delay by `delay` on each attempt
- **exponential** – doubles the delay on each attempt

## Requirements

- Python 3.8+
- No external dependencies

## License

This project is licensed under the [MIT License](LICENSE).