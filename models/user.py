from typing import TYPE_CHECKING, List
from uuid import UUID, uuid4

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimeStampMixin

if TYPE_CHECKING:
    from models.order import Order


class User(Base, TimeStampMixin):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(40), nullable=False)

    orders: Mapped[List["Order"]] = relationship(
        back_populates="user", lazy="select"
    )  # not using cascade as do not want orders to be delete when user is deleted and also not want "all" for now.
