"""
Zoom Server-to-Server OAuth integration.
Creates and manages Zoom meetings for bookings.
"""
import httpx
import base64
import time as time_module
from datetime import datetime
from typing import Optional, Tuple
from app.config import get_settings

# Token cache
_token_cache = {
    "access_token": None,
    "expires_at": 0
}


async def _get_access_token() -> str:
    """
    Get a valid Zoom access token using Server-to-Server OAuth.
    Caches token and refreshes when expired.
    """
    settings = get_settings()

    # Return cached token if still valid (with 60s buffer)
    if (_token_cache["access_token"]
            and _token_cache["expires_at"] > time_module.time() + 60):
        return _token_cache["access_token"]

    # Request new token
    credentials = f"{settings.zoom_client_id}:{settings.zoom_client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://zoom.us/oauth/token",
            params={
                "grant_type": "account_credentials",
                "account_id": settings.zoom_account_id,
            },
            headers={
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        if response.status_code != 200:
            raise Exception(
                f"Failed to get Zoom access token: {response.status_code} - {response.text}"
            )

        data = response.json()
        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = time_module.time() + data.get("expires_in", 3600)

        return _token_cache["access_token"]


async def create_zoom_meeting(
    topic: str,
    start_time: datetime,
    duration: int
) -> Tuple[str, str]:
    """
    Create a Zoom meeting.

    Args:
        topic: Meeting topic/title
        start_time: Meeting start time (UTC datetime)
        duration: Meeting duration in minutes

    Returns:
        Tuple of (join_url, meeting_id)
    """
    settings = get_settings()

    # Check if using placeholder credentials
    if settings.zoom_client_id == "placeholder":
        # Return mock data for development
        mock_id = f"mock-{int(time_module.time())}"
        return (
            f"https://zoom.us/j/{mock_id}",
            mock_id
        )

    token = await _get_access_token()

    meeting_data = {
        "topic": f"MindFuelByAli - {topic}",
        "type": 2,  # Scheduled meeting
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration": duration,
        "timezone": "UTC",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "join_before_host": True,
            "waiting_room": False,
            "auto_recording": "none",
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.zoom.us/v2/users/me/meetings",
            json=meeting_data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code not in (200, 201):
            raise Exception(
                f"Failed to create Zoom meeting: {response.status_code} - {response.text}"
            )

        data = response.json()
        return (data["join_url"], str(data["id"]))


async def delete_zoom_meeting(meeting_id: str) -> bool:
    """
    Delete a Zoom meeting (best-effort, used on cancellation).

    Args:
        meeting_id: The Zoom meeting ID to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    settings = get_settings()

    # Skip if using placeholder credentials
    if settings.zoom_client_id == "placeholder":
        return True

    if not meeting_id or meeting_id.startswith("mock-"):
        return True

    try:
        token = await _get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.zoom.us/v2/meetings/{meeting_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                },
            )

            return response.status_code == 204
    except Exception:
        # Best-effort deletion — don't fail the cancel flow
        return False
