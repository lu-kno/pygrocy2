from datetime import datetime
from enum import Enum

from pygrocy2.base import DataModel
from pygrocy2.data_models.user import User
from pygrocy2.grocy_api_client import (
    ChoreLogDetailsResponse,
    CurrentChoreLogResponse,
    GrocyApiClient,
)


class PeriodType(str, Enum):
    MANUALLY = "manually"
    DYNAMIC_REGULAR = "dynamic-regular"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ADAPTIVE = "adaptive"
    HOURLY = "hourly"


class AssignmentType(str, Enum):
    NO_ASSIGNMENT = "no-assignment"
    WHO_LEAST_DID_FIRST = "who-least-did-first"
    RANDOM = "random"
    IN_ALPHABETICAL_ORDER = "in-alphabetical-order"


class ChoreLog(DataModel):
    def __init__(self, response):
        if isinstance(response, CurrentChoreLogResponse):
            self._init_from_CurrentChoreLogResponse(response)
        elif isinstance(response, ChoreLogDetailsResponse):
            self._init_from_ChoreLogDetailsResponse(response) # TODO: maybe not needed

    # noinspection PyPep8Naming
    def _init_from_CurrentChoreLogResponse(self, response: CurrentChoreLogResponse): # TODO: Needs checking
        self._id = response.id # TODO: maybe just response.id or response.chore_log_id
        self._chore_id = response.chore_id
        self._tracked_time = response.tracked_time
        self._done_by = User(response.done_by_user_id)
        self._row_created_timestamp = response.row_created_timestamp
        self._undone = response.undone
        self._undone_timestamp = response.undone_timestamp
        self._skipped = response.skipped
        self._scheduled_execution_time = response.scheduled_execution_time

    # noinspection PyPep8Naming
    def _init_from_ChoreLogDetailsResponse(self, response: ChoreLogDetailsResponse): # TODO: maybe not needed
        chore_log_data = response.chore_log
        self._id = chore_log_data.id 
        self._chore_id = chore_log_data.chore_id
        self._tracked_time = chore_log_data.tracked_time
        self._done_by = User(chore_log_data.done_by_user_id)
        self._row_created_timestamp = chore_log_data.row_created_timestamp
        self._undone = chore_log_data.undone
        self._undone_timestamp = chore_log_data.undone_timestamp
        self._skipped = chore_log_data.skipped
        self._scheduled_execution_time = chore_log_data.scheduled_execution_time


    def get_details(self, api_client: GrocyApiClient):
        details = api_client.get_chore_log(self.id)
        self._init_from_ChoreDetailsResponse(details)
        self._userfields = api_client.get_userfields("chores_log", self.id)




    @property
    def id(self) -> int:
        return self._id

    @property
    def chore_id(self) -> int:
        return self._chore_id

    @property
    def tracked_time(self) -> datetime:
        return self._tracked_time

    @property
    def done_by(self) -> User:
        return self._done_by

    @property
    def row_created_timestamp(self) -> datetime:
        return self._row_created_timestamp

    @property
    def undone(self) -> bool:
        return self._undone

    @property
    def undone_timestamp(self) -> datetime:
        return self._undone_timestamp

    @property
    def skipped(self) -> bool:
        return self._skipped

    @property
    def scheduled_execution_time(self) -> datetime:
        return self._scheduled_execution_time

    @property
    def userfields(self) -> dict[str, str]:
        return self._userfields

