from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    role = Column(String, default="employee", nullable=False) # 'employee' or 'manager'
    hashed_password = Column(String, nullable=False)

class TimePunch(Base):
    __tablename__ = "time_punches"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("users.employee_id"), nullable=False)
    punch_type = Column(String, nullable=False) # 'CLOCK_IN' or 'CLOCK_OUT'
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
