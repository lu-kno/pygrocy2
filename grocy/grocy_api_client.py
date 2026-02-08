import base64  # noqa: D100
from datetime import datetime
from enum import Enum
import json
import logging
from typing import Any
from urllib.parse import urljoin

from pydantic import BaseModel, Field, field_validator, model_validator
import requests

from .data_models.generic import EntityType
from .errors import GrocyError
from .utils import grocy_datetime_str, localize_datetime, parse_date

DEFAULT_PORT_NUMBER = 9192

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


def _field_not_empty_validator(field_name: str):
    """Reusable Pydantic field pre-validator to convert empty str to None."""
    return field_validator(field_name, mode="before")(_none_if_empty_str)


def _none_if_empty_str(value: Any):
    if isinstance(value, str) and value == "":
        return None
    return value


class ShoppingListItem(BaseModel):
    id: int
    product_id: int | None = None
    note: str | None = None
    amount: float | None = None
    row_created_timestamp: datetime
    shopping_list_id: int
    done: int


class MealPlanResponse(BaseModel):
    id: int
    day: datetime
    type: str
    recipe_id: int | None = None
    recipe_servings: int | None = None
    note: str | None = None
    product_id: int | None = None
    product_amount: float | None = None
    product_qu_id: str | None = None
    row_created_timestamp: datetime
    userfields: dict | None = None
    section_id: int | None = None


class RecipeDetailsResponse(BaseModel):
    id: int | None = None
    name: str
    description: str | None = None
    base_servings: int
    desired_servings: int
    picture_file_name: str | None = None
    row_created_timestamp: datetime
    userfields: dict | None = None


class QuantityUnitData(BaseModel):
    id: int
    name: str
    name_plural: str | None = None
    description: str | None = None
    row_created_timestamp: datetime


class LocationData(BaseModel):
    id: int
    name: str
    description: str | None = None
    row_created_timestamp: datetime


class ProductData(BaseModel):
    id: int
    name: str
    description: str | None = None
    location_id: int | None = None
    product_group_id: int | None = None
    qu_id_stock: int
    qu_id_purchase: int
    picture_file_name: str | None = None
    allow_partial_units_in_stock: bool | None = False
    row_created_timestamp: datetime
    min_stock_amount: float | None = None
    default_best_before_days: int

    location_id_validator = _field_not_empty_validator("location_id")
    product_group_id_validator = _field_not_empty_validator("product_group_id")


class ChoreData(BaseModel):
    id: int
    name: str
    description: str | None = None
    period_type: str
    period_config: str | None = None
    period_days: int | None = 0
    track_date_only: bool
    rollover: bool
    assignment_type: str | None = None
    assignment_config: str | None = None
    next_execution_assigned_to_user_id: int | None = None
    userfields: dict | None = None

    next_execution_assigned_to_user_id_validator = _field_not_empty_validator(
        "next_execution_assigned_to_user_id"
    )


class UserDto(BaseModel):
    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None


class CurrentChoreResponse(BaseModel):
    chore_id: int
    last_tracked_time: datetime | None = None
    next_estimated_execution_time: datetime | None = None


class CurrentStockResponse(BaseModel):
    product_id: int
    amount: float
    best_before_date: datetime
    amount_opened: float
    amount_aggregated: float
    amount_opened_aggregated: float
    is_aggregated_amount: bool
    product: ProductData


class MissingProductResponse(BaseModel):
    id: int
    name: str
    amount_missing: float
    is_partly_in_stock: bool


class CurrentVolatileStockResponse(BaseModel):
    due_products: list[CurrentStockResponse] | None = None
    overdue_products: list[CurrentStockResponse] | None = None
    expired_products: list[CurrentStockResponse] | None = None
    missing_products: list[MissingProductResponse] | None = None


class ProductBarcodeData(BaseModel):
    barcode: str
    amount: float | None = None


class ProductDetailsResponse(BaseModel):
    last_purchased: datetime | None = None
    last_used: datetime | None = None
    stock_amount: float
    stock_amount_opened: float
    next_best_before_date: datetime | None = None
    last_price: float | None = None
    product: ProductData
    quantity_unit_stock: QuantityUnitData
    default_quantity_unit_purchase: QuantityUnitData
    barcodes: list[ProductBarcodeData] | None = Field(None, alias="product_barcodes")
    location: LocationData | None = None


class ChoreDetailsResponse(BaseModel):
    chore: ChoreData
    last_tracked: datetime | None = None
    next_estimated_execution_time: datetime | None = None
    track_count: int = 0
    next_execution_assigned_user: UserDto | None = None
    last_done_by: UserDto | None = None


class TransactionType(Enum):
    PURCHASE = "purchase"
    CONSUME = "consume"
    INVENTORY_CORRECTION = "inventory-correction"
    PRODUCT_OPENED = "product-opened"


class TaskCategoryDto(BaseModel):
    id: int
    name: str
    description: str | None = None
    row_created_timestamp: datetime


class TaskResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    due_date: datetime | None = None
    done: int
    done_timestamp: datetime | None = None
    category_id: int | None = None
    category: TaskCategoryDto | None = None
    assigned_to_user_id: int | None = None
    assigned_to_user: UserDto | None = None
    userfields: dict | None = None

    due_date_validator = _field_not_empty_validator("due_date")
    category_id_validator = _field_not_empty_validator("category_id")
    assigned_to_user_id_validator = _field_not_empty_validator("assigned_to_user_id")


class CurrentBatteryResponse(BaseModel):
    id: int
    last_tracked_time: datetime | None = None
    next_estimated_charge_time: datetime | None = None


class BatteryData(BaseModel):
    id: int
    name: str
    description: str | None = None
    used_in: str | None = None
    charge_interval_days: int
    created_timestamp: datetime = Field(alias="row_created_timestamp")
    userfields: dict | None = None


class BatteryDetailsResponse(BaseModel):
    battery: BatteryData
    charge_cycles_count: int
    last_charged: datetime | None = None
    last_tracked_time: datetime | None = None
    next_estimated_charge_time: datetime | None = None


class EquipmentData(BaseModel):
    id: int
    name: str
    description: str | None = None
    instruction_manual_file_name: str | None = None
    created_timestamp: datetime = Field(alias="row_created_timestamp")
    userfields: dict | None = None


class EquipmentDetailsResponse(BaseModel):
    equipment: EquipmentData


class MealPlanSectionResponse(BaseModel):
    id: int | None = None
    name: str | None = None
    sort_number: int | None = None
    row_created_timestamp: datetime

    sort_number_validator = _field_not_empty_validator("sort_number")


class StockLogResponse(BaseModel):
    id: int
    product_id: int
    amount: float
    best_before_date: datetime
    purchased_date: datetime
    used_date: datetime | None = None
    spoiled: bool = False
    stock_id: str
    transaction_id: str
    transaction_type: TransactionType


class GrocyVersionDto(BaseModel):
    version: str = Field(alias="Version")
    release_date: datetime = Field(alias="ReleaseDate")


class SystemInfoDto(BaseModel):
    grocy_version_info: GrocyVersionDto = Field(alias="grocy_version")
    php_version: str
    sqlite_version: str
    os: str
    client: str


class SystemTimeDto(BaseModel):
    timezone: str
    time_local: datetime
    time_local_sqlite3: datetime
    time_utc: datetime
    timestamp: int


class SystemConfigDto(BaseModel, extra="allow"):
    username: str = Field(alias="USER_USERNAME")
    base_path: str = Field(alias="BASE_PATH")
    base_url: str = Field(alias="BASE_URL")
    mode: str = Field(alias="MODE")
    default_locale: str = Field(alias="DEFAULT_LOCALE")
    locale: str = Field(alias="LOCALE")
    currency: str = Field(alias="CURRENCY")
    feature_flags: dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def feature_flags_root_validator(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Pydantic root validator to add all "FEATURE_FLAG_" settings to Dict."""
        features: dict[str, Any] = {}

        for field, value in data.items():
            if field.startswith("FEATURE_FLAG_"):
                features[field] = value

        data["feature_flags"] = features

        return data


# --- New response models for additional API endpoints ---


class StockEntryResponse(BaseModel):
    id: int
    product_id: int
    amount: float
    best_before_date: datetime | None = None
    purchased_date: datetime | None = None
    stock_id: str
    price: float | None = None
    location_id: int | None = None
    shopping_location_id: int | None = None
    opened_date: datetime | None = None
    row_created_timestamp: datetime | None = None


class StockLocationResponse(BaseModel):
    product_id: int
    location_id: int
    amount: float


class PriceHistoryResponse(BaseModel):
    date: datetime
    price: float
    shopping_location_id: int | None = None


class RecipeFulfillmentResponse(BaseModel):
    recipe_id: int
    need_fulfilled: bool
    need_fulfilled_with_shopping_list: bool
    missing_products_count: int | None = None


class StockBookingResponse(BaseModel):
    id: int
    product_id: int
    amount: float
    best_before_date: datetime | None = None
    purchased_date: datetime | None = None
    stock_id: str
    transaction_id: str
    transaction_type: str
    row_created_timestamp: datetime | None = None


def _enable_debug_mode():
    _LOGGER.setLevel(logging.DEBUG)


class GrocyApiClient(object):
    def __init__(
        self,
        base_url,
        api_key,
        port: int = DEFAULT_PORT_NUMBER,
        path: str | None = None,
        verify_ssl=True,
        debug=False,
    ):
        if debug:
            _enable_debug_mode()

        if path:
            self._base_url = f"{base_url}:{port}/{path}/api/"
        else:
            self._base_url = f"{base_url}:{port}/api/"
        _LOGGER.debug(f"generated base url: {self._base_url}")

        self._api_key = api_key
        self._verify_ssl = verify_ssl
        if self._api_key == "demo_mode":
            self._headers = {"accept": "application/json"}
        else:
            self._headers = {"accept": "application/json", "GROCY-API-KEY": api_key}

    def _do_get_request(self, end_url: str, query_filters: list[str] | None = None):
        req_url = urljoin(self._base_url, end_url)
        params = None
        if query_filters:
            params = {"query[]": query_filters}
        resp = requests.get(
            req_url, verify=self._verify_ssl, headers=self._headers, params=params
        )

        _LOGGER.debug("-->\tGET /%s", end_url)
        _LOGGER.debug("<--\t%d for /%s", resp.status_code, end_url)
        _LOGGER.debug("\t\t%s", resp.content)

        if resp.status_code >= 400:
            raise GrocyError(resp)

        if len(resp.content) > 0:
            return resp.json()
        return None

    def _do_post_request(self, end_url: str, data: dict):
        req_url = urljoin(self._base_url, end_url)
        resp = requests.post(
            req_url, verify=self._verify_ssl, headers=self._headers, json=data
        )

        _LOGGER.debug("-->\tPOST /%s", end_url)
        _LOGGER.debug("\t\t%s", data)
        _LOGGER.debug("<--\t%d for /%s", resp.status_code, end_url)
        _LOGGER.debug("\t\t%s", resp.content)

        if resp.status_code >= 400:
            raise GrocyError(resp)
        if len(resp.content) > 0:
            return resp.json()
        return None

    def _do_put_request(self, end_url: str, data):
        req_url = urljoin(self._base_url, end_url)
        up_header = self._headers.copy()
        up_header["accept"] = "*/*"
        if isinstance(data, dict):
            up_header["Content-Type"] = "application/json"
            data = json.dumps(data)
        else:
            up_header["Content-Type"] = "application/octet-stream"
        resp = requests.put(
            req_url, verify=self._verify_ssl, headers=up_header, data=data
        )

        _LOGGER.debug("-->\tPUT /%s", end_url)
        _LOGGER.debug("\t\t%s", data)
        _LOGGER.debug("<--\t%d for /%s", resp.status_code, end_url)
        _LOGGER.debug("\t\t%s", resp.content)

        if resp.status_code >= 400:
            raise GrocyError(resp)

        if len(resp.content) > 0:
            return resp.json()
        return None

    def _do_delete_request(self, end_url: str):
        req_url = urljoin(self._base_url, end_url)
        resp = requests.delete(req_url, verify=self._verify_ssl, headers=self._headers)

        _LOGGER.debug("-->\tDELETE /%s", end_url)
        _LOGGER.debug("<--\t%d for /%s", resp.status_code, end_url)
        _LOGGER.debug("\t\t%s", resp.content)

        if resp.status_code >= 400:
            raise GrocyError(resp)

        if len(resp.content) > 0:
            return resp.json()
        return None

    # --- Stock ---

    def get_stock(self) -> list[CurrentStockResponse]:
        parsed_json = self._do_get_request("stock")
        if parsed_json:
            return [CurrentStockResponse(**response) for response in parsed_json]
        return []

    def get_volatile_stock(self) -> CurrentVolatileStockResponse:
        parsed_json = self._do_get_request("stock/volatile")
        return CurrentVolatileStockResponse(**parsed_json)

    def get_product(self, product_id) -> ProductDetailsResponse:
        url = f"stock/products/{product_id}"
        parsed_json = self._do_get_request(url)
        if parsed_json:
            return ProductDetailsResponse(**parsed_json)
        return None

    def get_product_by_barcode(self, barcode) -> ProductDetailsResponse:
        url = f"stock/products/by-barcode/{barcode}"
        parsed_json = self._do_get_request(url)
        if parsed_json:
            return ProductDetailsResponse(**parsed_json)
        return None

    def add_product(
        self,
        product_id,
        amount: float,
        price: float,
        best_before_date: datetime | None = None,
        transaction_type: TransactionType = TransactionType.PURCHASE,
    ):
        data = {
            "amount": amount,
            "transaction_type": transaction_type.value,
            "price": price,
        }

        if best_before_date is not None:
            data["best_before_date"] = best_before_date.strftime("%Y-%m-%d")

        return self._do_post_request(f"stock/products/{product_id}/add", data)

    def consume_product(
        self,
        product_id: int,
        amount: float = 1,
        spoiled: bool = False,
        transaction_type: TransactionType = TransactionType.CONSUME,
        allow_subproduct_substitution: bool = False,
    ):
        data = {
            "amount": amount,
            "spoiled": spoiled,
            "transaction_type": transaction_type.value,
            "allow_subproduct_substitution": allow_subproduct_substitution,
        }

        self._do_post_request(f"stock/products/{product_id}/consume", data)

    def open_product(
        self,
        product_id: int,
        amount: float = 1,
        allow_subproduct_substitution: bool = False,
    ):
        data = {
            "amount": amount,
            "allow_subproduct_substitution": allow_subproduct_substitution,
        }

        self._do_post_request(f"stock/products/{product_id}/open", data)

    def inventory_product(
        self,
        product_id: int,
        new_amount: float,
        best_before_date: datetime = None,
        shopping_location_id: int = None,
        location_id: int = None,
        price: float = None,
    ):
        data = {
            "new_amount": new_amount,
        }

        if best_before_date is not None:
            data["best_before_date"] = localize_datetime(best_before_date).strftime(
                "%Y-%m-%d"
            )
        if shopping_location_id is not None:
            data["shopping_location_id"] = shopping_location_id

        if location_id is not None:
            data["location_id"] = location_id

        if price is not None:
            data["price"] = price

        parsed_json = self._do_post_request(
            f"stock/products/{product_id}/inventory", data
        )

        if parsed_json:
            stockLog = [StockLogResponse(**response) for response in parsed_json]
            return stockLog[0]
        return None

    def add_product_by_barcode(
        self,
        barcode: str,
        amount: float,
        price: float,
        best_before_date: datetime | None = None,
    ) -> StockLogResponse:
        data = {
            "amount": amount,
            "transaction_type": TransactionType.PURCHASE.value,
            "price": price,
        }

        if best_before_date is not None:
            data["best_before_date"] = localize_datetime(best_before_date).strftime(
                "%Y-%m-%d"
            )

        parsed_json = self._do_post_request(
            f"stock/products/by-barcode/{barcode}/add", data
        )

        if parsed_json:
            stockLog = [StockLogResponse(**response) for response in parsed_json]
            return stockLog[0]
        return None

    def consume_product_by_barcode(
        self, barcode: str, amount: float = 1, spoiled: bool = False
    ):
        data = {
            "amount": amount,
            "spoiled": spoiled,
            "transaction_type": TransactionType.CONSUME.value,
        }

        parsed_json = self._do_post_request(
            f"stock/products/by-barcode/{barcode}/consume", data
        )

        if parsed_json:
            stockLog = [StockLogResponse(**response) for response in parsed_json]
            return stockLog[0]
        return None

    def inventory_product_by_barcode(
        self,
        barcode: str,
        new_amount: float,
        best_before_date: datetime | None = None,
        location_id: int | None = None,
        price: float | None = None,
    ):
        data = {
            "new_amount": new_amount,
        }

        if best_before_date is not None:
            data["best_before_date"] = localize_datetime(best_before_date).strftime(
                "%Y-%m-%d"
            )

        if location_id is not None:
            data["location_id"] = location_id

        if price is not None:
            data["price"] = price

        parsed_json = self._do_post_request(
            f"stock/products/by-barcode/{barcode}/inventory", data
        )

        if parsed_json:
            stockLog = [StockLogResponse(**response) for response in parsed_json]
            return stockLog[0]
        return None

    def transfer_product(
        self,
        product_id: int,
        amount: float,
        location_from: int,
        location_to: int,
    ):
        data = {
            "amount": amount,
            "location_id_from": location_from,
            "location_id_to": location_to,
        }
        return self._do_post_request(f"stock/products/{product_id}/transfer", data)

    def open_product_by_barcode(self, barcode: str, amount: float = 1):
        data = {"amount": amount}
        return self._do_post_request(f"stock/products/by-barcode/{barcode}/open", data)

    def transfer_product_by_barcode(
        self,
        barcode: str,
        amount: float,
        location_from: int,
        location_to: int,
    ):
        data = {
            "amount": amount,
            "location_id_from": location_from,
            "location_id_to": location_to,
        }
        return self._do_post_request(
            f"stock/products/by-barcode/{barcode}/transfer", data
        )

    def merge_products(self, product_id_keep: int, product_id_remove: int):
        return self._do_post_request(
            f"stock/products/{product_id_keep}/merge/{product_id_remove}", {}
        )

    def get_stock_entry(self, entry_id: int) -> StockEntryResponse | None:
        parsed_json = self._do_get_request(f"stock/entry/{entry_id}")
        if parsed_json:
            return StockEntryResponse(**parsed_json)
        return None

    def edit_stock_entry(self, entry_id: int, data: dict):
        return self._do_put_request(f"stock/entry/{entry_id}", data)

    def get_product_stock_entries(self, product_id: int) -> list[StockEntryResponse]:
        parsed_json = self._do_get_request(f"stock/products/{product_id}/entries")
        if parsed_json:
            return [StockEntryResponse(**e) for e in parsed_json]
        return []

    def get_product_stock_locations(
        self, product_id: int
    ) -> list[StockLocationResponse]:
        parsed_json = self._do_get_request(f"stock/products/{product_id}/locations")
        if parsed_json:
            return [StockLocationResponse(**loc) for loc in parsed_json]
        return []

    def get_product_price_history(self, product_id: int) -> list[PriceHistoryResponse]:
        parsed_json = self._do_get_request(f"stock/products/{product_id}/price-history")
        if parsed_json:
            return [PriceHistoryResponse(**p) for p in parsed_json]
        return []

    def get_stock_entries_by_location(
        self, location_id: int
    ) -> list[StockEntryResponse]:
        parsed_json = self._do_get_request(f"stock/locations/{location_id}/entries")
        if parsed_json:
            return [StockEntryResponse(**e) for e in parsed_json]
        return []

    def get_stock_booking(self, booking_id: int) -> StockBookingResponse | None:
        parsed_json = self._do_get_request(f"stock/bookings/{booking_id}")
        if parsed_json:
            return StockBookingResponse(**parsed_json)
        return None

    def undo_stock_booking(self, booking_id: int):
        return self._do_post_request(f"stock/bookings/{booking_id}/undo", {})

    def get_stock_transactions(self, transaction_id: str) -> list[StockLogResponse]:
        parsed_json = self._do_get_request(f"stock/transactions/{transaction_id}")
        if parsed_json:
            return [StockLogResponse(**t) for t in parsed_json]
        return []

    def undo_stock_transaction(self, transaction_id: str):
        return self._do_post_request(f"stock/transactions/{transaction_id}/undo", {})

    def external_barcode_lookup(self, barcode: str):
        return self._do_get_request(f"stock/barcodes/external-lookup/{barcode}")

    # --- Chores ---

    def get_chores(
        self, query_filters: list[str] | None = None
    ) -> list[CurrentChoreResponse]:
        parsed_json = self._do_get_request("chores", query_filters)
        if parsed_json:
            return [CurrentChoreResponse(**chore) for chore in parsed_json]
        return []

    def get_chore(self, chore_id: int) -> ChoreDetailsResponse:
        url = f"chores/{chore_id}"
        parsed_json = self._do_get_request(url)
        if parsed_json:
            return ChoreDetailsResponse(**parsed_json)
        return None

    def execute_chore(
        self,
        chore_id: int,
        done_by: int | None = None,
        tracked_time: datetime | None = None,
        skipped: bool = False,
    ):
        if tracked_time is None:
            tracked_time = datetime.now()

        localized_tracked_time = localize_datetime(tracked_time)

        data = {
            "tracked_time": grocy_datetime_str(localized_tracked_time),
            "skipped": skipped,
        }

        if done_by is not None:
            data["done_by"] = done_by

        return self._do_post_request(f"chores/{chore_id}/execute", data)

    def undo_chore_execution(self, execution_id: int):
        return self._do_post_request(f"chores/executions/{execution_id}/undo", {})

    def calculate_chore_assignments(self):
        return self._do_post_request("chores/executions/calculate-next-assignments", {})

    def merge_chores(self, chore_id_keep: int, chore_id_remove: int):
        return self._do_post_request(
            f"chores/{chore_id_keep}/merge/{chore_id_remove}", {}
        )

    # --- Recipes ---

    def consume_recipe(
        self,
        recipe_id: int,
    ):
        self._do_post_request(f"recipes/{recipe_id}/consume", None)

    def get_recipe(self, object_id: int) -> RecipeDetailsResponse:
        parsed_json = self._do_get_request(f"objects/recipes/{object_id}")
        if parsed_json:
            return RecipeDetailsResponse(**parsed_json)
        return None

    def get_recipe_fulfillment(
        self, recipe_id: int
    ) -> RecipeFulfillmentResponse | None:
        parsed_json = self._do_get_request(f"recipes/{recipe_id}/fulfillment")
        if parsed_json:
            return RecipeFulfillmentResponse(**parsed_json)
        return None

    def get_all_recipes_fulfillment(self) -> list[RecipeFulfillmentResponse]:
        parsed_json = self._do_get_request("recipes/fulfillment")
        if parsed_json:
            return [RecipeFulfillmentResponse(**r) for r in parsed_json]
        return []

    def add_not_fulfilled_to_shopping_list(self, recipe_id: int):
        return self._do_post_request(
            f"recipes/{recipe_id}/add-not-fulfilled-products-to-shoppinglist", {}
        )

    def copy_recipe(self, recipe_id: int):
        return self._do_post_request(f"recipes/{recipe_id}/copy", {})

    # --- Shopping List ---

    def get_shopping_list(
        self, query_filters: list[str] = None
    ) -> list[ShoppingListItem]:
        parsed_json = self._do_get_request("objects/shopping_list", query_filters)
        if parsed_json:
            return [ShoppingListItem(**response) for response in parsed_json]
        return []

    def add_missing_product_to_shopping_list(self, shopping_list_id: int = None):
        data = None
        if shopping_list_id:
            data = {"list_id": shopping_list_id}

        self._do_post_request("stock/shoppinglist/add-missing-products", data)

    def add_product_to_shopping_list(
        self,
        product_id: int,
        shopping_list_id: int = 1,
        amount: float = 1,
        quantity_unit_id: int = None,
    ):
        data = {
            "product_id": product_id,
            "list_id": shopping_list_id,
            "product_amount": amount,
        }
        if quantity_unit_id:
            data["qu_id"] = quantity_unit_id
        self._do_post_request("stock/shoppinglist/add-product", data)

    def clear_shopping_list(self, shopping_list_id: int = 1):
        data = {"list_id": shopping_list_id}

        self._do_post_request("stock/shoppinglist/clear", data)

    def remove_product_in_shopping_list(
        self, product_id: int, shopping_list_id: int = 1, amount: float = 1
    ):
        data = {
            "product_id": product_id,
            "list_id": shopping_list_id,
            "product_amount": amount,
        }
        self._do_post_request("stock/shoppinglist/remove-product", data)

    def add_overdue_products_to_shopping_list(self, shopping_list_id: int = 1):
        data = {"list_id": shopping_list_id}
        self._do_post_request("stock/shoppinglist/add-overdue-products", data)

    def add_expired_products_to_shopping_list(self, shopping_list_id: int = 1):
        data = {"list_id": shopping_list_id}
        self._do_post_request("stock/shoppinglist/add-expired-products", data)

    # --- Product groups ---

    def get_product_groups(
        self, query_filters: list[str] | None = None
    ) -> list[LocationData]:
        parsed_json = self._do_get_request("objects/product_groups", query_filters)
        if parsed_json:
            return [LocationData(**response) for response in parsed_json]
        return []

    # --- Product pictures ---

    def upload_product_picture(self, product_id: int, pic_path: str):
        b64fn = base64.b64encode(f"{product_id}.jpg".encode("ascii"))
        req_url = "files/productpictures/" + str(b64fn, "utf-8")
        with open(pic_path, "rb") as pic:  # noqa: PTH123
            self._do_put_request(req_url, pic)

    def update_product_pic(self, product_id: int):
        pic_name = f"{product_id}.jpg"
        data = {"picture_file_name": pic_name}
        self._do_put_request(f"objects/products/{product_id}", data)

    # --- Userfields ---

    def get_userfields(self, entity: str, object_id: int):
        url = f"userfields/{entity}/{object_id}"
        return self._do_get_request(url)

    def set_userfields(self, entity: str, object_id: int, key: str, value):
        data = {key: value}
        self._do_put_request(f"userfields/{entity}/{object_id}", data)

    # --- System ---

    def get_last_db_changed(self):
        resp = self._do_get_request("system/db-changed-time")
        return parse_date(resp.get("changed_time"))

    def get_system_info(self) -> SystemInfoDto:
        parsed_json = self._do_get_request("system/info")
        if parsed_json:
            return SystemInfoDto(**parsed_json)

    def get_system_time(self) -> SystemTimeDto:
        parsed_json = self._do_get_request("system/time")
        if parsed_json:
            return SystemTimeDto(**parsed_json)

    def get_system_config(self) -> SystemConfigDto:
        parsed_json = self._do_get_request("system/config")
        _LOGGER.debug("System config: %s", parsed_json)
        if parsed_json:
            return SystemConfigDto(**parsed_json)

    # --- Tasks ---

    def get_tasks(self, query_filters: list[str] | None = None) -> list[TaskResponse]:
        parsed_json = self._do_get_request("tasks", query_filters)
        if parsed_json:
            return [TaskResponse(**data) for data in parsed_json]
        return []

    def get_task(self, task_id: int) -> TaskResponse:
        url = f"objects/tasks/{task_id}"
        parsed_json = self._do_get_request(url)
        return TaskResponse(**parsed_json)

    def complete_task(self, task_id: int, done_time: datetime | None = None):
        url = f"tasks/{task_id}/complete"

        if done_time is None:
            done_time = datetime.now()

        localized_done_time = localize_datetime(done_time)

        data = {"done_time": grocy_datetime_str(localized_done_time)}
        self._do_post_request(url, data)

    def undo_task(self, task_id: int):
        return self._do_post_request(f"tasks/{task_id}/undo", {})

    # --- Meal plan ---

    def get_meal_plan(
        self, query_filters: list[str] | None = None
    ) -> list[MealPlanResponse]:
        parsed_json = self._do_get_request("objects/meal_plan", query_filters)
        if parsed_json:
            return [MealPlanResponse(**data) for data in parsed_json]
        return []

    def get_meal_plan_sections(
        self, query_filters: list[str] | None = None
    ) -> list[MealPlanSectionResponse]:
        parsed_json = self.get_generic_objects_for_type(
            EntityType.MEAL_PLAN_SECTIONS, query_filters
        )
        if parsed_json:
            return [MealPlanSectionResponse(**resp) for resp in parsed_json]
        return []

    def get_meal_plan_section(self, meal_plan_section_id) -> MealPlanSectionResponse:
        parsed_json = self._do_get_request(
            f"objects/meal_plan_sections?query%5B%5D=id%3D{meal_plan_section_id}"
        )
        if parsed_json and len(parsed_json) == 1:
            return MealPlanSectionResponse(**parsed_json[0])
        return None

    # --- Batteries ---

    def get_batteries(
        self, query_filters: list[str] | None = None
    ) -> list[CurrentBatteryResponse]:
        parsed_json = self._do_get_request("batteries", query_filters)
        if parsed_json:
            return [CurrentBatteryResponse(**data) for data in parsed_json]
        return []

    def get_battery(self, battery_id: int) -> BatteryDetailsResponse:
        parsed_json = self._do_get_request(f"batteries/{battery_id}")
        if parsed_json:
            return BatteryDetailsResponse(**parsed_json)
        return None

    def charge_battery(self, battery_id: int, tracked_time: datetime | None = None):
        if tracked_time is None:
            tracked_time = datetime.now()

        localized_tracked_time = localize_datetime(tracked_time)
        data = {"tracked_time": grocy_datetime_str(localized_tracked_time)}

        return self._do_post_request(f"batteries/{battery_id}/charge", data)

    def undo_battery_charge(self, charge_cycle_id: int):
        return self._do_post_request(
            f"batteries/charge-cycles/{charge_cycle_id}/undo", {}
        )

    # --- Generic CRUD ---

    def add_generic(self, entity_type: str, data):
        return self._do_post_request(f"objects/{entity_type}", data)

    def get_generic(self, entity_type: str, object_id: int):
        return self._do_get_request(f"objects/{entity_type}/{object_id}")

    def update_generic(self, entity_type: str, object_id: int, data):
        return self._do_put_request(f"objects/{entity_type}/{object_id}", data)

    def delete_generic(self, entity_type: str, object_id: int):
        return self._do_delete_request(f"objects/{entity_type}/{object_id}")

    def get_generic_objects_for_type(
        self, entity_type: str | Enum, query_filters: list[str] | None = None
    ):
        if isinstance(entity_type, Enum):
            entity_type = entity_type.value
        return self._do_get_request(f"objects/{entity_type}", query_filters)

    # --- Equipment ---

    def get_equipment(self, equipment_id: int) -> EquipmentDetailsResponse:
        """Get details of a specific equipment item."""
        parsed_json = self._do_get_request(f"objects/equipment/{equipment_id}")
        if parsed_json:
            equipment_data = EquipmentData(**parsed_json)
            return EquipmentDetailsResponse(equipment=equipment_data)
        return None

    def get_all_equipment(self, query_filters: list[str] = None) -> list[dict]:
        """Get all equipment items."""
        return self._do_get_request("objects/equipment", query_filters) or []

    # --- Users ---

    def get_users(self) -> list[UserDto]:
        parsed_json = self._do_get_request("users")
        if parsed_json:
            return [UserDto(**user) for user in parsed_json]
        return []

    def get_user(self, user_id: int) -> UserDto:
        query_params = []
        if user_id:
            query_params.append(f"id={user_id}")
        parsed_json = self._do_get_request("users")
        if parsed_json:
            return UserDto(**parsed_json[0])
        return None

    def get_current_user(self) -> UserDto | None:
        parsed_json = self._do_get_request("user")
        if parsed_json:
            return UserDto(**parsed_json)
        return None

    def create_user(self, data: dict):
        return self._do_post_request("users", data)

    def edit_user(self, user_id: int, data: dict):
        return self._do_put_request(f"users/{user_id}", data)

    def delete_user(self, user_id: int):
        return self._do_delete_request(f"users/{user_id}")

    def get_user_settings(self):
        return self._do_get_request("user/settings")

    def get_user_setting(self, key: str):
        return self._do_get_request(f"user/settings/{key}")

    def set_user_setting(self, key: str, value):
        return self._do_put_request(f"user/settings/{key}", {"value": value})

    def delete_user_setting(self, key: str):
        return self._do_delete_request(f"user/settings/{key}")

    # --- Calendar ---

    def get_calendar_ical(self) -> str | None:
        return self._do_get_request("calendar/ical")

    def get_calendar_sharing_link(self) -> str | None:
        return self._do_get_request("calendar/ical/sharing-link")

    # --- Files ---

    def upload_file(self, group: str, file_name: str, data):
        b64fn = base64.b64encode(file_name.encode("ascii"))
        req_url = f"files/{group}/" + str(b64fn, "utf-8")
        self._do_put_request(req_url, data)

    def download_file(self, group: str, file_name: str):
        b64fn = base64.b64encode(file_name.encode("ascii"))
        req_url = f"files/{group}/" + str(b64fn, "utf-8")
        return self._do_get_request(req_url)

    def delete_file(self, group: str, file_name: str):
        b64fn = base64.b64encode(file_name.encode("ascii"))
        req_url = f"files/{group}/" + str(b64fn, "utf-8")
        return self._do_delete_request(req_url)
