import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.database import Base

# ── Enums ─────────────────────────────────────────────────────────────────────
import enum

class OrderStatus(str, enum.Enum):
    pending   = "pending"
    confirmed = "confirmed"
    shipped   = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


# ── Order table ───────────────────────────────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"

    order_id     : Mapped[str]   = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      : Mapped[str]   = mapped_column(String(36), nullable=False, index=True)
    status       : Mapped[str]   = mapped_column(SAEnum(OrderStatus), default=OrderStatus.pending, nullable=False)
    total_amount : Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[str]  = mapped_column(String(50), nullable=True)
    created_at   : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at   : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # One order → many items
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",   # auto-load items when order is fetched
    )

    def to_dict(self) -> dict:
        return {
            "order_id":      self.order_id,
            "user_id":       self.user_id,
            "status":        self.status,
            "total_amount":  self.total_amount,
            "items":         [i.to_dict() for i in self.items],
            "created_at":    self.created_at.isoformat(),
            "updated_at":    self.updated_at.isoformat(),
        }


# ── OrderItem table ───────────────────────────────────────────────────────────
class OrderItem(Base):
    __tablename__ = "order_items"

    item_id      : Mapped[str]   = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id     : Mapped[str]   = mapped_column(String(36), ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False)
    product_id   : Mapped[str]   = mapped_column(String(36), nullable=False)
    quantity     : Mapped[int]   = mapped_column(Integer, nullable=False)
    unit_price   : Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "quantity":   self.quantity,
            "unit_price": self.unit_price,
        }
