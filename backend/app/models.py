from sqlalchemy import Column, Integer, String, Float, Date, DateTime, func

from .database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)  # income / expense
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    note = Column(String(200), nullable=True)
    txn_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
