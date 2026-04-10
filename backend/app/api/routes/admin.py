"""
Admin routes — protected by JWT session token.
Manage bookings, availability, and settings.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from app.models.schemas import (
    AdminLoginRequest, AdminLoginResponse,
    AvailabilityRequest, AvailabilityResponse,
    SettingsResponse, SettingsUpdateRequest,
    BookingDetail, BookingsListResponse,
    CancelResponse,
)
from app.db.supabase_client import supabase
from app.config import get_settings as get_app_settings, TZ_PKT
from app.services.availability import set_date_availability
from app.services.zoom import delete_zoom_meeting, end_zoom_meeting
from app.services.email import send_cancellation_email

router = APIRouter(prefix="/admin", tags=["Admin"])
security = HTTPBearer()

# JWT settings
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def _create_token(data: dict) -> str:
    """Create a JWT token."""
    settings = get_app_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def _verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token from Authorization header."""
    settings = get_app_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[ALGORITHM]
        )
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Not authorized.")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


# ─── Login ────────────────────────────────────────────────

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest):
    """Validate admin password and return session token."""
    settings = get_app_settings()

    if request.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid password.")

    token = _create_token({"role": "admin", "sub": "admin"})

    return AdminLoginResponse(token=token)


# ─── Bookings Management ─────────────────────────────────

@router.get("/bookings", response_model=BookingsListResponse)
async def list_bookings(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    _: dict = Depends(_verify_token),
):
    """List all bookings with optional filters."""
    query = supabase.table("bookings").select(
        "*, users!inner(name, email)"
    ).order("start_time", desc=True)

    if status:
        query = query.eq("status", status)

    if date:
        # Filter by date in PKT timezone
        from app.config import TZ_UTC
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        from datetime import time
        pkt_start = TZ_PKT.localize(datetime.combine(date_obj, time(0, 0)))
        pkt_end = TZ_PKT.localize(datetime.combine(date_obj, time(23, 59, 59)))

        utc_start = pkt_start.astimezone(TZ_UTC).isoformat()
        utc_end = pkt_end.astimezone(TZ_UTC).isoformat()

        query = query.gte("start_time", utc_start).lte("start_time", utc_end)

    result = query.execute()

    bookings = []
    for row in (result.data or []):
        user_data = row.get("users", {})
        bookings.append(BookingDetail(
            id=row["id"],
            user_name=user_data.get("name", "Unknown"),
            user_email=user_data.get("email", ""),
            booking_type=row["booking_type"],
            duration=row["duration"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            zoom_link=row.get("zoom_link"),
            zoom_meeting_id=row.get("zoom_meeting_id"),
            topic=row["topic"],
            status=row["status"],
            created_at=row["created_at"],
        ))

    return BookingsListResponse(bookings=bookings, total=len(bookings))


@router.get("/bookings/{booking_id}", response_model=BookingDetail)
async def get_booking(
    booking_id: str,
    _: dict = Depends(_verify_token),
):
    """Get a single booking by ID."""
    result = (
        supabase.table("bookings")
        .select("*, users!inner(name, email)")
        .eq("id", booking_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=404, detail="Booking not found.")

    row = result.data[0]
    user_data = row.get("users", {})

    return BookingDetail(
        id=row["id"],
        user_name=user_data.get("name", "Unknown"),
        user_email=user_data.get("email", ""),
        booking_type=row["booking_type"],
        duration=row["duration"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        zoom_link=row.get("zoom_link"),
        zoom_meeting_id=row.get("zoom_meeting_id"),
        topic=row["topic"],
        status=row["status"],
        created_at=row["created_at"],
    )


@router.delete("/bookings/{booking_id}", response_model=CancelResponse)
async def delete_booking(
    booking_id: str,
    _: dict = Depends(_verify_token),
):
    """Cancel a booking from admin panel."""
    # Find the booking
    result = (
        supabase.table("bookings")
        .select("*, users!inner(name, email)")
        .eq("id", booking_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=404, detail="Booking not found.")

    booking = result.data[0]

    if booking["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Booking is already cancelled.")

    # Cancel the booking
    supabase.table("bookings").update(
        {"status": "cancelled"}
    ).eq("id", booking_id).execute()

    # Delete Zoom meeting
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


@router.delete("/bookings/{booking_id}/permanent")
async def permanently_delete_booking(
    booking_id: str,
    _: dict = Depends(_verify_token),
):
    """Permanently remove a booking from the database."""
    # Find the booking first to get zoom info
    result = supabase.table("bookings").select("*").eq("id", booking_id).execute()
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=404, detail="Booking not found.")
    
    booking = result.data[0]
    
    # Delete Zoom meeting if it's still there
    if booking.get("status") == "scheduled" and booking.get("zoom_meeting_id"):
        try:
            await delete_zoom_meeting(booking["zoom_meeting_id"])
        except:
            pass # Already deleted or error

    # Delete from database
    supabase.table("bookings").delete().eq("id", booking_id).execute()

    return {"message": "Booking permanently deleted from database."}


@router.post("/bookings/bulk-cancel")
async def bulk_cancel_bookings(
    _: dict = Depends(_verify_token),
):
    """Cancel all upcoming scheduled bookings."""
    # Find all scheduled bookings
    result = (
        supabase.table("bookings")
        .select("*, users!inner(name, email)")
        .eq("status", "scheduled")
        .execute()
    )

    if not result.data or len(result.data) == 0:
        return {"cancelled_count": 0, "emails_sent": 0, "message": "No upcoming bookings to cancel."}

    bookings_to_cancel = result.data
    booking_ids = [b["id"] for b in bookings_to_cancel]

    # Update all to cancelled
    supabase.table("bookings").update(
        {"status": "cancelled"}
    ).in_("id", booking_ids).execute()

    emails_sent = 0
    # Process deletions and emails
    for booking in bookings_to_cancel:
        if booking.get("zoom_meeting_id"):
            await delete_zoom_meeting(booking["zoom_meeting_id"])
        
        user_data = booking.get("users", {})
        success = await send_cancellation_email(
            user_email=user_data.get("email", ""),
            user_name=user_data.get("name", ""),
            booking_type=booking["booking_type"],
            start_time=booking["start_time"],
        )
        if success:
            emails_sent += 1

    return {
        "cancelled_count": len(bookings_to_cancel),
        "emails_sent": emails_sent,
        "message": f"Successfully cancelled {len(bookings_to_cancel)} meetings and sent {emails_sent} emails."
    }


@router.post("/sync-zoom-statuses")
async def sync_zoom_statuses(
    _: dict = Depends(_verify_token),
):
    """
    Check all scheduled meetings. 
    If they have passed their end_time, end the Zoom meeting and set status to completed.
    """
    now_utc = datetime.utcnow().isoformat()
    
    # Find scheduled bookings that have expired
    result = (
        supabase.table("bookings")
        .select("*")
        .eq("status", "scheduled")
        .lt("end_time", now_utc)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        return {"processed": 0, "ended_on_zoom": 0, "message": "No expired meetings to sync."}

    expired_bookings = result.data
    ended_count = 0
    
    for booking in expired_bookings:
        # Call Zoom to end the meeting
        if booking.get("zoom_meeting_id"):
            success = await end_zoom_meeting(booking["zoom_meeting_id"])
            if success:
                ended_count += 1
        
        # Update status to completed in DB
        supabase.table("bookings").update(
            {"status": "completed"}
        ).eq("id", booking["id"]).execute()

    return {
        "processed": len(expired_bookings),
        "ended_on_zoom": ended_count,
        "message": f"Successfully processed {len(expired_bookings)} expired meetings. {ended_count} ended on Zoom."
    }

# ─── Availability Management ─────────────────────────────

@router.post("/availability", response_model=AvailabilityResponse)
async def update_availability(
    request: AvailabilityRequest,
    _: dict = Depends(_verify_token),
):
    """Set a specific date as available or unavailable."""
    try:
        await set_date_availability(request.date, request.is_available)
        status_text = "available" if request.is_available else "unavailable"
        return AvailabilityResponse(
            date=request.date,
            is_available=request.is_available,
            message=f"Date {request.date} has been set as {status_text}.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update availability: {str(e)}"
        )


@router.get("/availability")
async def get_availability(
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    _: dict = Depends(_verify_token),
):
    """Get availability records, optionally filtered by month."""
    query = supabase.table("availability").select("*").order("date")

    if month:
        # Filter by month
        start = f"{month}-01"
        # Calculate end of month
        year, mon = month.split("-")
        if int(mon) == 12:
            end = f"{int(year) + 1}-01-01"
        else:
            end = f"{year}-{int(mon) + 1:02d}-01"
        query = query.gte("date", start).lt("date", end)

    result = query.execute()
    return {"availability": result.data or []}


# ─── Settings Management ─────────────────────────────────

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    _: dict = Depends(_verify_token),
):
    """Get current admin settings."""
    result = supabase.table("settings").select("*").limit(1).execute()

    if not result.data or len(result.data) == 0:
        return SettingsResponse(
            daily_start_time="17:00",
            daily_end_time="21:00",
            is_booking_enabled=True,
        )

    row = result.data[0]
    # Format time strings
    start_time = row["daily_start_time"]
    end_time = row["daily_end_time"]

    # Ensure HH:MM format
    if len(start_time) > 5:
        start_time = start_time[:5]
    if len(end_time) > 5:
        end_time = end_time[:5]

    return SettingsResponse(
        daily_start_time=start_time,
        daily_end_time=end_time,
        is_booking_enabled=row["is_booking_enabled"],
        available_days=row.get("available_days", [1,2,3,4,5,6,0])
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    _: dict = Depends(_verify_token),
):
    """Update admin settings (time range, booking toggle)."""
    # Get current settings
    result = supabase.table("settings").select("*").limit(1).execute()

    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=500, detail="Settings not initialized.")

    settings_id = result.data[0]["id"]
    current = result.data[0]

    # Build update payload
    update_data = {"updated_at": datetime.utcnow().isoformat()}

    if request.daily_start_time is not None:
        update_data["daily_start_time"] = request.daily_start_time
    if request.daily_end_time is not None:
        update_data["daily_end_time"] = request.daily_end_time
    if request.is_booking_enabled is not None:
        update_data["is_booking_enabled"] = request.is_booking_enabled
    if request.available_days is not None:
        update_data["available_days"] = request.available_days

    supabase.table("settings").update(update_data).eq("id", settings_id).execute()

    # Return updated settings
    final_start = request.daily_start_time or current["daily_start_time"]
    final_end = request.daily_end_time or current["daily_end_time"]
    final_enabled = request.is_booking_enabled if request.is_booking_enabled is not None else current["is_booking_enabled"]

    if len(final_start) > 5:
        final_start = final_start[:5]
    if len(final_end) > 5:
        final_end = final_end[:5]

    return SettingsResponse(
        daily_start_time=final_start,
        daily_end_time=final_end,
        is_booking_enabled=final_enabled,
        available_days=request.available_days if request.available_days is not None else current.get("available_days", [1,2,3,4,5,6,0])
    )
