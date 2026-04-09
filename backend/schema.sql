-- ============================================================
-- MindFuelByAli — Supabase Database Schema
-- Run this in the Supabase SQL Editor
-- ============================================================

-- Enable UUID extension (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Custom Types ───────────────────────────────────────────

-- Booking type enum
DO $$ BEGIN
    CREATE TYPE booking_type AS ENUM ('consultation', 'project_discussion');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Booking status enum
DO $$ BEGIN
    CREATE TYPE booking_status AS ENUM ('scheduled', 'cancelled', 'completed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ─── Users Table ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index on email for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ─── Bookings Table ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    booking_type booking_type NOT NULL,
    duration INTEGER NOT NULL CHECK (duration IN (10, 30)),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    zoom_link TEXT,
    zoom_meeting_id TEXT,
    topic TEXT NOT NULL CHECK (char_length(topic) <= 300),
    status booking_status NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bookings_start_time ON bookings(start_time);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_date_status ON bookings(start_time, status);

-- ─── Availability Table ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS availability (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,
    is_available BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_availability_date ON availability(date);

-- ─── Settings Table ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    daily_start_time TIME NOT NULL DEFAULT '21:00:00',
    daily_end_time TIME NOT NULL DEFAULT '23:59:59',
    is_booking_enabled BOOLEAN NOT NULL DEFAULT true,
    available_days JSONB NOT NULL DEFAULT '[1,2,3,4,5,6,0]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default settings row (only if table is empty)
INSERT INTO settings (daily_start_time, daily_end_time, is_booking_enabled, available_days)
SELECT '21:00:00', '23:59:59', true, '[1,2,3,4,5,6,0]'
WHERE NOT EXISTS (SELECT 1 FROM settings);

-- ─── Row Level Security ─────────────────────────────────────
-- Service role key bypasses RLS, so these are for additional safety

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (service role bypasses RLS by default)
-- These policies are for any anon/authenticated access if ever needed

CREATE POLICY "Service role full access on users"
    ON users FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on bookings"
    ON bookings FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on availability"
    ON availability FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on settings"
    ON settings FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- Schema setup complete!
-- Default settings: 5 PM – 9 PM PKT, booking enabled
-- ============================================================
