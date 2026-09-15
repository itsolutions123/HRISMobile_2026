from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    position = Column(String, nullable=True)
    department = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    mobile_phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    birthday = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    civil_status = Column(String, nullable=True)
    agency = Column(String, nullable=True)

class JobCategory(Base):
    __tablename__ = "job_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    description = Column(String, nullable=True)

    sub_items = relationship("JobSubItem", back_populates="category", cascade="all, delete-orphan")

class JobSubItem(Base):
    __tablename__ = "job_sub_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("job_categories.id"))
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)

    category = relationship("JobCategory", back_populates="sub_items")

class PunchLog(Base):
    __tablename__ = "punch_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, index=True, nullable=False)
    punch_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    address = Column(String, nullable=True)
