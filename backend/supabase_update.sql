-- Run this in your Supabase SQL Editor to update your existing settings table!

ALTER TABLE settings ADD COLUMN IF NOT EXISTS available_days JSONB NOT NULL DEFAULT '[1,2,3,4,5,6,0]';

UPDATE settings SET daily_start_time = '21:00:00', daily_end_time = '23:59:59';
