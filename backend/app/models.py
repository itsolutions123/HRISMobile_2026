from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False, default="Head Office")
    position = Column(String, nullable=False, default="Staff")
    role = Column(String, default="employee", nullable=False) # 'super_admin', 'manager', 'employee'
    hashed_password = Column(String, nullable=False)

class DepartmentGroup(Base):
    __tablename__ = "department_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

class TimePunch(Base):
    __tablename__ = "time_punches"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("users.employee_id"), nullable=False)
    punch_type = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
