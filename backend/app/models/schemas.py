"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from enum import Enum
from datetime import datetime, date, time


# ─── Enums ────────────────────────────────────────────────

class BookingType(str, Enum):
    consultation = "consultation"
    project_discussion = "project_discussion"


class BookingStatus(str, Enum):
    scheduled = "scheduled"
    cancelled = "cancelled"
    completed = "completed"


# ─── Slot Schemas ─────────────────────────────────────────

class SlotInfo(BaseModel):
    start: str  # "17:00"
    end: str    # "17:10"
    available: bool


class SlotsResponse(BaseModel):
    date: str
    timezone: str = "Asia/Karachi"
    slots: List[SlotInfo]


# ─── Booking Schemas ─────────────────────────────────────

class BookingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    booking_type: BookingType
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    topic: str = Field(..., min_length=1, max_length=300)


class BookingResponse(BaseModel):
    booking_id: str
    zoom_link: str
    start_time: str
    end_time: str
    message: str = "Booking confirmed. Check your email."


class CancelRequest(BaseModel):
    booking_id: str


class CancelResponse(BaseModel):
    message: str = "Booking cancelled successfully."


class RescheduleRequest(BaseModel):
    booking_id: str
    new_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    new_start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")


class RescheduleResponse(BaseModel):
    new_booking_id: str
    zoom_link: str
    start_time: str
    end_time: str
    message: str = "Booking rescheduled successfully. Check your email for new details."


# ─── Admin Schemas ────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    message: str = "Login successful."


class AvailabilityRequest(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    is_available: bool


class AvailabilityResponse(BaseModel):
    date: str
    is_available: bool
    message: str


class SettingsResponse(BaseModel):
    daily_start_time: str
    daily_end_time: str
    is_booking_enabled: bool
    available_days: List[int]


class SettingsUpdateRequest(BaseModel):
    daily_start_time: Optional[str] = None  # "HH:MM"
    daily_end_time: Optional[str] = None    # "HH:MM"
    is_booking_enabled: Optional[bool] = None
    available_days: Optional[List[int]] = None


class BookingDetail(BaseModel):
    id: str
    user_name: str
    user_email: str
    booking_type: str
    duration: int
    start_time: str
    end_time: str
    zoom_link: Optional[str] = None
    zoom_meeting_id: Optional[str] = None
    topic: str
    status: str
    created_at: str


class BookingsListResponse(BaseModel):
    bookings: List[BookingDetail]
    total: int
