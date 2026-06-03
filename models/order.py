from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimeStampMixin

if TYPE_CHECKING:
    from models.user import User


class Status(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Order(Base, TimeStampMixin):
    __tablename__ = "orders"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[Status] = mapped_column(
        SQLEnum(Status),
        default=Status.PENDING,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="orders", lazy="select")
