"""
Availability service — manages time slots and date availability.
"""
from datetime import datetime, date, time, timedelta
from typing import List, Dict
from app.db.supabase_client import supabase
from app.config import TZ_UTC, TZ_PKT, SLOT_DURATION, CONSULTATION_DURATION, PROJECT_DISCUSSION_DURATION
import pytz


async def is_booking_enabled() -> bool:
    """Check the global booking enabled toggle."""
    try:
        result = supabase.table("settings").select("is_booking_enabled").limit(1).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]["is_booking_enabled"]
        return False
    except Exception as e:
        print(f"[AVAILABILITY] Error checking booking enabled: {e}")
        return False


async def get_settings() -> Dict:
    """Get current admin settings."""
    try:
        result = supabase.table("settings").select("*").limit(1).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        # Default settings
        return {
            "daily_start_time": "21:00:00",  # 9 PM PKT = 16:00 UTC
            "daily_end_time": "23:59:59",    # 12 AM PKT = 18:59:59 UTC
            "is_booking_enabled": True,
            "available_days": [1,2,3,4,5,6,0]
        }
    except Exception as e:
        print(f"[AVAILABILITY] Error getting settings: {e}")
        return {
            "daily_start_time": "21:00:00",
            "daily_end_time": "23:59:59",
            "is_booking_enabled": True,
            "available_days": [1,2,3,4,5,6,0]
        }


async def is_date_available(target_date: str) -> bool:
    """
    Check if a specific date is available for booking.
    Returns True if no record exists (default available) or if is_available is True.
    """
    try:
        result = (
            supabase.table("availability")
            .select("is_available")
            .eq("date", target_date)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]["is_available"]
        # No record means available by default
        return True
    except Exception as e:
        print(f"[AVAILABILITY] Error checking date: {e}")
        return True


async def get_existing_bookings(target_date: str) -> List[Dict]:
    """
    Get all active (scheduled) bookings for a specific date.
    target_date should be in YYYY-MM-DD format.
    """
    try:
        # Convert date to UTC range for the day
        date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()

        # Create PKT start/end of day, then convert to UTC
        pkt_start = TZ_PKT.localize(datetime.combine(date_obj, time(0, 0)))
        pkt_end = TZ_PKT.localize(datetime.combine(date_obj, time(23, 59, 59)))

        utc_start = pkt_start.astimezone(TZ_UTC).isoformat()
        utc_end = pkt_end.astimezone(TZ_UTC).isoformat()

        result = (
            supabase.table("bookings")
            .select("start_time, end_time, duration, status")
            .gte("start_time", utc_start)
            .lte("start_time", utc_end)
            .eq("status", "scheduled")
            .execute()
        )

        return result.data if result.data else []
    except Exception as e:
        print(f"[AVAILABILITY] Error getting bookings: {e}")
        return []


async def generate_slots(target_date: str) -> List[Dict]:
    """
    Generate available time slots for a given date.

    All internal processing is in UTC, but the slots returned
    are formatted in PKT for display.
    """
    # Check global toggle
    if not await is_booking_enabled():
        return []

    # Get admin settings
    settings = await get_settings()

    date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    # Check date availability overrides and weekly schedule
    try:
        ovr_result = supabase.table("availability").select("is_available").eq("date", target_date).execute()
        explicitly_blocked = False
        explicitly_enabled = False
        if ovr_result.data and len(ovr_result.data) > 0:
            if not ovr_result.data[0]["is_available"]:
                explicitly_blocked = True
            else:
                explicitly_enabled = True
    except:
        explicitly_blocked = False
        explicitly_enabled = False

    js_weekday = (date_obj.weekday() + 1) % 7
    normally_available = js_weekday in settings.get("available_days", [1,2,3,4,5,6,0])

    if explicitly_blocked:
        return []
    if not normally_available and not explicitly_enabled:
        return []

    # Parse daily time window (stored as UTC times in HH:MM:SS format)
    start_time_str = settings["daily_start_time"]
    end_time_str = settings["daily_end_time"]

    # Parse time strings
    start_parts = start_time_str.split(":")
    end_parts = end_time_str.split(":")
    window_start = time(int(start_parts[0]), int(start_parts[1]))
    window_end = time(int(end_parts[0]), int(end_parts[1]))

    # Create UTC datetimes for the slot window
    date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()

    # The times in settings are stored as PKT times, so we convert to UTC
    pkt_start = TZ_PKT.localize(datetime.combine(date_obj, window_start))
    pkt_end = TZ_PKT.localize(datetime.combine(date_obj, window_end))

    utc_start = pkt_start.astimezone(TZ_UTC)
    utc_end = pkt_end.astimezone(TZ_UTC)

    # Get existing bookings
    existing_bookings = await get_existing_bookings(target_date)

    # Parse existing booking time ranges
    booked_ranges = []
    for booking in existing_bookings:
        b_start = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00"))
        b_end = datetime.fromisoformat(booking["end_time"].replace("Z", "+00:00"))
        booked_ranges.append((b_start, b_end))

    # Generate 10-minute slots
    slots = []
    current = utc_start
    while current + timedelta(minutes=SLOT_DURATION) <= utc_end:
        slot_end = current + timedelta(minutes=SLOT_DURATION)

        # Check if this slot overlaps with any booking
        is_available = True
        for b_start, b_end in booked_ranges:
            if current < b_end and slot_end > b_start:
                is_available = False
                break

        # Convert to PKT for display
        pkt_slot_start = current.astimezone(TZ_PKT)
        pkt_slot_end = slot_end.astimezone(TZ_PKT)

        slots.append({
            "start": pkt_slot_start.strftime("%H:%M"),
            "end": pkt_slot_end.strftime("%H:%M"),
            "available": is_available,
        })

        current = slot_end

    return slots


async def check_slots_available(
    target_date: str,
    start_time_str: str,
    duration: int
) -> bool:
    """
    Check if a specific time range is available for booking.

    Args:
        target_date: Date in YYYY-MM-DD format
        start_time_str: Start time in HH:MM format (PKT)
        duration: Duration in minutes (10 or 30)

    Returns:
        True if all required slots are available
    """
    # Parse the requested time (in PKT)
    date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    time_parts = start_time_str.split(":")
    slot_time = time(int(time_parts[0]), int(time_parts[1]))

    pkt_start = TZ_PKT.localize(datetime.combine(date_obj, slot_time))
    pkt_end = pkt_start + timedelta(minutes=duration)

    utc_start = pkt_start.astimezone(TZ_UTC)
    utc_end = pkt_end.astimezone(TZ_UTC)

    # Get existing bookings for the date
    existing_bookings = await get_existing_bookings(target_date)

    # Check for overlap with any existing booking
    for booking in existing_bookings:
        b_start = datetime.fromisoformat(booking["start_time"].replace("Z", "+00:00"))
        b_end = datetime.fromisoformat(booking["end_time"].replace("Z", "+00:00"))

        if utc_start < b_end and utc_end > b_start:
            return False

    return True


async def set_date_availability(target_date: str, available: bool) -> Dict:
    """
    Set a specific date as available or unavailable.
    Uses upsert to handle both insert and update.
    """
    try:
        result = (
            supabase.table("availability")
            .upsert(
                {"date": target_date, "is_available": available},
                on_conflict="date"
            )
            .execute()
        )
        return {"date": target_date, "is_available": available}
    except Exception as e:
        print(f"[AVAILABILITY] Error setting date availability: {e}")
        raise
