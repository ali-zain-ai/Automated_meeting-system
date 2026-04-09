"""
Public booking endpoints — create, cancel, and reschedule bookings.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, time, timedelta
from app.models.schemas import (
    BookingRequest, BookingResponse,
    CancelRequest, CancelResponse,
    RescheduleRequest, RescheduleResponse,
    BookingType,
)
from app.services.availability import (
    is_booking_enabled, is_date_available, check_slots_available
)
from app.services.zoom import create_zoom_meeting, delete_zoom_meeting
from app.services.email import (
    send_booking_confirmation, send_admin_notification, send_cancellation_email
)
from app.db.supabase_client import supabase
from app.config import (
    TZ_UTC, TZ_PKT,
    CONSULTATION_DURATION, PROJECT_DISCUSSION_DURATION
)

router = APIRouter(tags=["Bookings"])


def _get_duration(booking_type: BookingType) -> int:
    """Get duration in minutes based on booking type."""
    if booking_type == BookingType.project_discussion:
        return PROJECT_DISCUSSION_DURATION
    return CONSULTATION_DURATION


async def _get_or_create_user(name: str, email: str) -> str:
    """Find existing user by email or create a new one. Returns user ID."""
    # Try to find existing user
    result = (
        supabase.table("users")
        .select("id")
        .eq("email", email)
        .execute()
    )

    if result.data and len(result.data) > 0:
        # Update name if changed
        supabase.table("users").update({"name": name}).eq("email", email).execute()
        return result.data[0]["id"]

    # Create new user
    result = (
        supabase.table("users")
        .insert({"name": name, "email": email})
        .execute()
    )

    if result.data and len(result.data) > 0:
        return result.data[0]["id"]

    raise HTTPException(status_code=500, detail="Failed to create user record.")


@router.post("/book", response_model=BookingResponse)
async def create_booking(request: BookingRequest):
    """
    Create a new booking, generate a Zoom meeting, and send emails.
    """
    # Check global toggle
    if not await is_booking_enabled():
        raise HTTPException(
            status_code=403,
            detail="Booking is currently disabled. Please try again later."
        )

    # Check date availability
    if not await is_date_available(request.date):
        raise HTTPException(
            status_code=400,
            detail="This date is not available for booking."
        )

    # Validate date isn't in the past
    try:
        date_obj = datetime.strptime(request.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format.")

    today_pkt = datetime.now(TZ_PKT).date()
    if date_obj < today_pkt:
        raise HTTPException(status_code=400, detail="Cannot book for past dates.")

    # Determine duration
    duration = _get_duration(request.booking_type)

    # Check if the requested slots are available
    is_available = await check_slots_available(
        request.date, request.start_time, duration
    )
    if not is_available:
        raise HTTPException(
            status_code=409,
            detail="The selected time slot is no longer available. Please choose another."
        )

    # Calculate start and end times in UTC
    time_parts = request.start_time.split(":")
    slot_time = time(int(time_parts[0]), int(time_parts[1]))

    pkt_start = TZ_PKT.localize(datetime.combine(date_obj, slot_time))
    pkt_end = pkt_start + timedelta(minutes=duration)

    utc_start = pkt_start.astimezone(TZ_UTC)
    utc_end = pkt_end.astimezone(TZ_UTC)

    # Get or create user
    user_id = await _get_or_create_user(request.name, request.email)

    # Create Zoom meeting
    try:
        zoom_link, zoom_meeting_id = await create_zoom_meeting(
            topic=request.topic,
            start_time=utc_start,
            duration=duration,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Zoom meeting: {str(e)}"
        )

    # Insert booking into database
    booking_data = {
        "user_id": user_id,
        "booking_type": request.booking_type.value,
        "duration": duration,
        "start_time": utc_start.isoformat(),
        "end_time": utc_end.isoformat(),
        "zoom_link": zoom_link,
        "zoom_meeting_id": zoom_meeting_id,
        "topic": request.topic,
        "status": "scheduled",
    }

    result = supabase.table("bookings").insert(booking_data).execute()

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create booking.")

    booking_id = result.data[0]["id"]

    # Send emails (fire and forget — don't fail the booking if email fails)
    await send_booking_confirmation(
        user_email=request.email,
        user_name=request.name,
        booking_type=request.booking_type.value,
        start_time=utc_start.isoformat(),
        zoom_link=zoom_link,
        topic=request.topic,
    )

    await send_admin_notification(
        user_name=request.name,
        user_email=request.email,
        booking_type=request.booking_type.value,
        duration=duration,
        start_time=utc_start.isoformat(),
        topic=request.topic,
        zoom_link=zoom_link,
    )

    return BookingResponse(
        booking_id=booking_id,
        zoom_link=zoom_link,
        start_time=pkt_start.isoformat(),
        end_time=pkt_end.isoformat(),
        message="Booking confirmed. Check your email.",
    )


@router.post("/cancel", response_model=CancelResponse)
async def cancel_booking(request: CancelRequest):
    """
    Cancel a booking by ID, delete Zoom meeting, and send cancellation email.
    """
    # Find the booking
    result = (
        supabase.table("bookings")
        .select("*, users!inner(name, email)")
        .eq("id", request.booking_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=404, detail="Booking not found.")

    booking = result.data[0]

    if booking["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="This booking is already cancelled.")

    # Update status to cancelled
    supabase.table("bookings").update(
        {"status": "cancelled"}
    ).eq("id", request.booking_id).execute()

    # Delete Zoom meeting (best-effort)
    if booking.get("zoom_meeting_id"):
        await delete_zoom_meeting(booking["zoom_meeting_id"])

    # Send cancellation email
    user_data = booking.get("users", {})
    await send_cancellation_email(
        user_email=user_data.get("email", ""),
        user_name=user_data.get("name", ""),
        booking_type=booking["booking_type"],
        start_time=booking["start_time"],
    )

    return CancelResponse(message="Booking cancelled successfully.")


@router.post("/reschedule", response_model=RescheduleResponse)
async def reschedule_booking(request: RescheduleRequest):
    """
    Reschedule a booking — cancels old one and creates a new one.
    Generates new Zoom link and sends new confirmation email.
    """
    # Find the existing booking
    result = (
        supabase.table("bookings")
        .select("*, users!inner(name, email)")
        .eq("id", request.booking_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=404, detail="Booking not found.")

    old_booking = result.data[0]

    if old_booking["status"] != "scheduled":
        raise HTTPException(
            status_code=400,
            detail="Only scheduled bookings can be rescheduled."
        )

    user_data = old_booking.get("users", {})
    user_name = user_data.get("name", "")
    user_email = user_data.get("email", "")

    # Cancel the old booking
    supabase.table("bookings").update(
        {"status": "cancelled"}
    ).eq("id", request.booking_id).execute()

    # Delete old Zoom meeting (best-effort)
    if old_booking.get("zoom_meeting_id"):
        await delete_zoom_meeting(old_booking["zoom_meeting_id"])

    # Create new booking at new slot
    booking_type = BookingType(old_booking["booking_type"])
    duration = old_booking["duration"]

    # Check new slot availability
    is_available = await check_slots_available(
        request.new_date, request.new_start_time, duration
    )
    if not is_available:
        # Revert cancellation
        supabase.table("bookings").update(
            {"status": "scheduled"}
        ).eq("id", request.booking_id).execute()
        raise HTTPException(
            status_code=409,
            detail="The new time slot is not available. Original booking kept."
        )

    # Calculate new times
    date_obj = datetime.strptime(request.new_date, "%Y-%m-%d").date()
    time_parts = request.new_start_time.split(":")
    slot_time = time(int(time_parts[0]), int(time_parts[1]))

    pkt_start = TZ_PKT.localize(datetime.combine(date_obj, slot_time))
    pkt_end = pkt_start + timedelta(minutes=duration)

    utc_start = pkt_start.astimezone(TZ_UTC)
    utc_end = pkt_end.astimezone(TZ_UTC)

    # Create new Zoom meeting
    zoom_link, zoom_meeting_id = await create_zoom_meeting(
        topic=old_booking["topic"],
        start_time=utc_start,
        duration=duration,
    )

    # Insert new booking
    new_booking_data = {
        "user_id": old_booking["user_id"],
        "booking_type": old_booking["booking_type"],
        "duration": duration,
        "start_time": utc_start.isoformat(),
        "end_time": utc_end.isoformat(),
        "zoom_link": zoom_link,
        "zoom_meeting_id": zoom_meeting_id,
        "topic": old_booking["topic"],
        "status": "scheduled",
    }

    new_result = supabase.table("bookings").insert(new_booking_data).execute()

    if not new_result.data or len(new_result.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create rescheduled booking.")

    new_booking_id = new_result.data[0]["id"]

    # Send new confirmation email
    await send_booking_confirmation(
        user_email=user_email,
        user_name=user_name,
        booking_type=old_booking["booking_type"],
        start_time=utc_start.isoformat(),
        zoom_link=zoom_link,
        topic=old_booking["topic"],
    )

    # Send admin notification
    await send_admin_notification(
        user_name=user_name,
        user_email=user_email,
        booking_type=old_booking["booking_type"],
        duration=duration,
        start_time=utc_start.isoformat(),
        topic=old_booking["topic"],
        zoom_link=zoom_link,
    )

    return RescheduleResponse(
        new_booking_id=new_booking_id,
        zoom_link=zoom_link,
        start_time=pkt_start.isoformat(),
        end_time=pkt_end.isoformat(),
    )
