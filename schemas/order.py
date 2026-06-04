from typing import Annotated
from uuid import UUID, uuid4

from pydantic import Field

from models.order import Status
from schemas.user import CamelCase


class Order(CamelCase):
    customer_name: str
    amount: float
    status: Status


class CreateOrder(Order):
    pass


class ReadOrder(CamelCase):
    id: UUID
    customer_id: UUID
    amount: float
    status: Status
