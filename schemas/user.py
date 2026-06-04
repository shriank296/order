from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class User(CamelCase):
    name: str


class CreateUser(User):
    pass


class ReadUser(User):
    id: UUID
    created_at: datetime
    updated_at: datetime
