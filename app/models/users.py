from sqlalchemy import String, Boolean, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship  # New

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[int] = mapped_column(String, default='buyer')

    products: Mapped[list["Product"]] = relationship("Product", back_populates="seller")
    categories: Mapped[list["Category"]] = relationship("Category", back_populates="admin")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="user")
    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="user", cascade="all, delete-orphan"
    )
