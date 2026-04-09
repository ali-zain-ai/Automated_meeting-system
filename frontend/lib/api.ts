/**
 * MindFuelByAli — API Client
 * Handles all communication with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Types ──────────────────────────────────────────────

export interface Slot {
  start: string;
  end: string;
  available: boolean;
}

export interface SlotsResponse {
  date: string;
  timezone: string;
  slots: Slot[];
}

export interface BookingRequest {
  name: string;
  email: string;
  booking_type: 'consultation' | 'project_discussion';
  date: string;
  start_time: string;
  topic: string;
}

export interface BookingResponse {
  booking_id: string;
  zoom_link: string;
  start_time: string;
  end_time: string;
  message: string;
}

export interface BookingDetail {
  id: string;
  user_name: string;
  user_email: string;
  booking_type: string;
  duration: number;
  start_time: string;
  end_time: string;
  zoom_link: string | null;
  zoom_meeting_id: string | null;
  topic: string;
  status: string;
  created_at: string;
}

export interface SettingsResponse {
  daily_start_time: string;
  daily_end_time: string;
  is_booking_enabled: boolean;
  available_days: number[];
}

export interface AvailabilityRecord {
  id: string;
  date: string;
  is_available: boolean;
}

// ─── API Functions ──────────────────────────────────────

async function apiFetch(path: string, options: RequestInit = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `API error: ${res.status}`);
  }

  return res.json();
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

// ─── Public Endpoints ───────────────────────────────────

export async function getSlots(date: string): Promise<SlotsResponse> {
  return apiFetch(`/slots?date=${date}`);
}

export async function createBooking(data: BookingRequest): Promise<BookingResponse> {
  return apiFetch('/book', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function cancelBooking(bookingId: string): Promise<{ message: string }> {
  return apiFetch('/cancel', {
    method: 'POST',
    body: JSON.stringify({ booking_id: bookingId }),
  });
}

export async function rescheduleBooking(
  bookingId: string,
  newDate: string,
  newStartTime: string
): Promise<BookingResponse> {
  return apiFetch('/reschedule', {
    method: 'POST',
    body: JSON.stringify({
      booking_id: bookingId,
      new_date: newDate,
      new_start_time: newStartTime,
    }),
  });
}

// ─── Admin Endpoints ────────────────────────────────────

export async function adminLogin(password: string): Promise<{ token: string }> {
  return apiFetch('/admin/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  });
}

export async function getAdminBookings(
  token: string,
  filters?: { date?: string; status?: string }
): Promise<{ bookings: BookingDetail[]; total: number }> {
  let path = '/admin/bookings';
  const params = new URLSearchParams();
  if (filters?.date) params.set('date', filters.date);
  if (filters?.status) params.set('status', filters.status);
  const qs = params.toString();
  if (qs) path += `?${qs}`;

  return apiFetch(path, { headers: authHeaders(token) });
}

export async function getAdminBookingDetail(
  token: string,
  bookingId: string
): Promise<BookingDetail> {
  return apiFetch(`/admin/bookings/${bookingId}`, { headers: authHeaders(token) });
}

export async function deleteAdminBooking(
  token: string,
  bookingId: string
): Promise<{ message: string }> {
  return apiFetch(`/admin/bookings/${bookingId}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
}

export async function permanentlyDeleteAdminBooking(
  token: string,
  bookingId: string
): Promise<{ message: string }> {
  return apiFetch(`/admin/bookings/${bookingId}/permanent`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
}

export async function bulkCancelAdminBookings(
  token: string
): Promise<{ cancelled_count: number; emails_sent: number; message: string }> {
  return apiFetch('/admin/bookings/bulk-cancel', {
    method: 'POST',
    headers: authHeaders(token),
  });
}

export async function setAvailability(
  token: string,
  date: string,
  isAvailable: boolean
): Promise<{ date: string; is_available: boolean; message: string }> {
  return apiFetch('/admin/availability', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ date, is_available: isAvailable }),
  });
}

export async function getAvailability(
  token: string,
  month?: string
): Promise<{ availability: AvailabilityRecord[] }> {
  let path = '/admin/availability';
  if (month) path += `?month=${month}`;
  return apiFetch(path, { headers: authHeaders(token) });
}

export async function getAdminSettings(token: string): Promise<SettingsResponse> {
  return apiFetch('/admin/settings', { headers: authHeaders(token) });
}

export async function updateAdminSettings(
  token: string,
  data: Partial<SettingsResponse>
): Promise<SettingsResponse> {
  return apiFetch('/admin/settings', {
    method: 'PUT',
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
}
