"""
Public slots endpoint — returns available time slots for a given date.
"""
from fastapi import APIRouter, Query, HTTPException
from app.models.schemas import SlotsResponse, SlotInfo
from app.services.availability import generate_slots, is_booking_enabled, is_date_available
from datetime import datetime

router = APIRouter(tags=["Slots"])


@router.get("/slots", response_model=SlotsResponse)
async def get_available_slots(
    date: str = Query(
        ...,
        description="Date to check slots for (YYYY-MM-DD format)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
):
    """
    Get available time slots for a specific date.
    All times returned in Asia/Karachi (PKT) timezone.
    """
    # Validate date format
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Don't allow past dates
    from app.config import TZ_PKT
    today_pkt = datetime.now(TZ_PKT).date()
    if date_obj < today_pkt:
        raise HTTPException(status_code=400, detail="Cannot check slots for past dates.")

    # Check global toggle
    if not await is_booking_enabled():
        raise HTTPException(
            status_code=403,
            detail="Booking is currently disabled. Please try again later."
        )

    # Check date availability
    if not await is_date_available(date):
        return SlotsResponse(
            date=date,
            timezone="Asia/Karachi",
            slots=[],
        )

    # Generate slots
    slots_data = await generate_slots(date)

    slots = [SlotInfo(**slot) for slot in slots_data]

    return SlotsResponse(
        date=date,
        timezone="Asia/Karachi",
        slots=slots,
    )
