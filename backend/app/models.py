import datetime as dt
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, JSON
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(50), nullable=False)
    company_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

    routes = relationship("RouteHistory", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_company_email"),)


class RouteHistory(Base):
    __tablename__ = "route_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    run_date = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    execution_date = Column(String(25), nullable=True)
    truck_assignments = Column(JSON, nullable=False)
    google_maps_links = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="routes")
