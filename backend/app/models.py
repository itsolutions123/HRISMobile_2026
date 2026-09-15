from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean
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
    suffix = Column(String, nullable=True)
    position = Column(String, nullable=True)
    department = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    mobile_phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    birthday = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    civil_status = Column(String, nullable=True)
    agency = Column(String, nullable=True)
    kiosk_code = Column(String, nullable=True)
    role = Column(String, default="Employee", nullable=False)  # 'Employee', 'Manager', 'Admin'
    status = Column(String, default="APPROVED", nullable=False) # 'PENDING', 'APPROVED', 'DENIED'
    created_at = Column(DateTime, default=datetime.utcnow)
    manager_id = Column(String, ForeignKey("employees.employee_id"), nullable=True)

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
    punch_type = Column(String, nullable=False)  # CLOCK_IN, CLOCK_OUT, BREAK_IN, BREAK_OUT
    timestamp = Column(DateTime, default=datetime.utcnow)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    job_sub_item_id = Column(Integer, ForeignKey("job_sub_items.id"), nullable=True)

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=True)
    group_id = Column(Integer, ForeignKey("schedule_groups.id"), nullable=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    shift_start = Column(String, nullable=False)   # HH:MM format
    shift_end = Column(String, nullable=False)     # HH:MM format
    break_duration_mins = Column(Integer, default=60)

class ScheduleGroup(Base):
    __tablename__ = "schedule_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "HO - Accounting"
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScheduleGroupAssignment(Base):
    __tablename__ = "schedule_group_assignments"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("schedule_groups.id"), nullable=False)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)

class DtrRevision(Base):
    __tablename__ = "dtr_revisions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    punch_log_id = Column(Integer, ForeignKey("punch_logs.id"), nullable=True)
    requested_punch_type = Column(String, nullable=False)  # CLOCK_IN, CLOCK_OUT, BREAK_IN, BREAK_OUT
    requested_timestamp = Column(DateTime, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    reviewed_by = Column(String, ForeignKey("employees.employee_id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.employee_id"), nullable=False)
    leave_type = Column(String, nullable=False)    # Sick, Vacation, etc.
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    approved_by = Column(String, ForeignKey("employees.employee_id"), nullable=True)
