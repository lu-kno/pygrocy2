# Getting Started

## Installation

```bash
pip install grocy-py
```

## Requirements

- Python >= 3.12
- A running [Grocy](https://grocy.info/) instance with API access

## Connecting to Grocy

```python
from grocy import Grocy

# Basic connection
grocy = Grocy("https://your-grocy-instance.com", "YOUR_API_KEY")

# With custom port and path
grocy = Grocy(
    "https://your-grocy-instance.com",
    "YOUR_API_KEY",
    port=9192,
    path="grocy",       # if Grocy is behind a subpath
    verify_ssl=True,
    debug=False,
)
```

The `Grocy` class constructs the API URL as `{base_url}:{port}/api/` (or `{base_url}:{port}/{path}/api/` when a path is provided).

## Local Development with Docker

The repository includes a `docker-compose.yml` that spins up a Grocy demo instance with a pre-seeded API key, so you can start experimenting immediately.

**Start the instance:**

```bash
docker compose up -d
```

This launches Grocy in demo mode on `localhost:9192` and automatically inserts a
known API key (`test_local_devenv`) into the demo database.

**Connect to it:**

```python
from grocy import Grocy

grocy = Grocy("http://localhost", "test_local_devenv", port=9192)

for product in grocy.stock.current():
    print(f"{product.name}: {product.available_amount}")
```

!!! tip
    Check out the [Example Notebook](example.ipynb) for a runnable walkthrough
    you can open in Jupyter.

## Working with Stock

```python
# Current stock
stock = grocy.stock.current()
for product in stock:
    print(f"{product.name}: {product.available_amount}")

# Add product to stock
grocy.stock.add(product_id=1, amount=5, price=2.99)

# Consume a product
grocy.stock.consume(product_id=1, amount=1)

# Open a product
grocy.stock.open(product_id=1)

# Products that are due, overdue, or expired
due = grocy.stock.due_products(get_details=True)
overdue = grocy.stock.overdue_products(get_details=True)
expired = grocy.stock.expired_products(get_details=True)
missing = grocy.stock.missing_products(get_details=True)

# Lookup by barcode
product = grocy.stock.product_by_barcode("4006381333931")
```

## Shopping Lists

```python
# Get shopping list items
items = grocy.shopping_list.items(get_details=True)
for item in items:
    print(f"{item.product.name}: {item.amount} (done: {item.done})")

# Add a product to the shopping list
grocy.shopping_list.add_product(product_id=1, amount=3)

# Add all missing products
grocy.shopping_list.add_missing_products()

# Clear the shopping list
grocy.shopping_list.clear()
```

## Chores

```python
from datetime import datetime

# List all chores
chores = grocy.chores.list(get_details=True)
for chore in chores:
    print(f"{chore.name} - next: {chore.next_estimated_execution_time}")

# Execute a chore
grocy.chores.execute(chore_id=1, done_by=1)
```

## Tasks

```python
# List tasks
tasks = grocy.tasks.list()
for task in tasks:
    print(f"{task.name} - due: {task.due_date}")

# Complete a task
grocy.tasks.complete(task_id=1)
```

## Batteries

```python
# List batteries
batteries = grocy.batteries.list(get_details=True)
for battery in batteries:
    print(f"{battery.name}: last charged {battery.last_charged}")

# Charge a battery
grocy.batteries.charge(battery_id=1)
```

## Meal Plans

```python
# Get meal plan items
meals = grocy.meal_plan.items(get_details=True)
for meal in meals:
    print(f"{meal.day}: {meal.recipe.name if meal.recipe else meal.note}")

# Get a recipe
recipe = grocy.recipes.get(recipe_id=1)
print(f"{recipe.name} ({recipe.base_servings} servings)")
```

## Generic CRUD Operations

For any Grocy entity type, you can use the generic CRUD methods:

```python
from grocy import Grocy
from grocy.data_models.generic import EntityType

grocy = Grocy("https://example.com", "API_KEY")

# List all objects of a type
locations = grocy.generic.list(EntityType.LOCATIONS)

# Get a single object
location = grocy.generic.get(EntityType.LOCATIONS, object_id=1)

# Create
grocy.generic.create(EntityType.LOCATIONS, {"name": "Pantry"})

# Update
grocy.generic.update(EntityType.LOCATIONS, object_id=1, data={"name": "Kitchen Pantry"})

# Delete
grocy.generic.delete(EntityType.LOCATIONS, object_id=1)
```

## The `get_details` Pattern

Many methods accept a `get_details=True` parameter. When enabled, each returned object makes an additional API call to fetch full details (name, barcodes, etc.). Without it, you only get the summary data from the list endpoint.

```python
# Summary only (1 API call)
stock = grocy.stock.current()

# Full details (1 + N API calls)
due = grocy.stock.due_products(get_details=True)
for product in due:
    print(product.name)       # available with details
    print(product.barcodes)   # available with details
```

## Error Handling

```python
from grocy.errors import GrocyError

try:
    grocy.stock.product(product_id=99999)
except GrocyError as e:
    print(f"HTTP {e.status_code}: {e.message}")
    if e.is_client_error:
        print("Client error (4xx)")
    elif e.is_server_error:
        print("Server error (5xx)")
```

## Debug Mode

Enable debug logging to see all HTTP requests and responses:

```python
grocy = Grocy("https://example.com", "API_KEY", debug=True)
```
