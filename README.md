# grocy-py
Check out [source code reference docs](https://iamkarlson.github.io/grocy-py/)

## Installation

`pip install grocy-py`

## Usage

Import the package:

```python
from grocy import Grocy
```

Obtain a grocy instance:

```python
grocy = Grocy("https://example.com", "GROCY_API_KEY")
```

or

```python
grocy = Grocy("https://example.com", "GROCY_API_KEY", port=9192, verify_ssl=True)
```

Get current stock:

```python
for entry in grocy.stock.current():
    print(f"{entry.available_amount} in stock for product id {entry.id}")
```

# Support

If you need help using grocy check the [discussions](https://github.com/iamkarlson/grocy-py/issues) section. Feel free to create an issue for feature requests, bugs and errors in the library.

## Development testing

You need [uv](https://docs.astral.sh/uv/) and Python 3.12+ to run the tests:

```bash
uv sync --group dev
uv run pytest
```
