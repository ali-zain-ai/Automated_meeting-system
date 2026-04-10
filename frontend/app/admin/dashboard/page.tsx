'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  getAdminBookings,
  getAdminSettings,
  updateAdminSettings,
  getAvailability,
  setAvailability,
  deleteAdminBooking,
  bulkCancelAdminBookings,
  permanentlyDeleteAdminBooking,
  BookingDetail,
  SettingsResponse,
  AvailabilityRecord,
} from '@/lib/api';
import {
  Sparkles,
  LogOut,
  Calendar as CalendarIcon,
  Video,
  XCircle,
  Trash2,
  Settings,
  RefreshCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Save,
} from 'lucide-react';
import styles from './page.module.css';

export default function AdminDashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string>('');
  
  // Data state
  const [bookings, setBookings] = useState<BookingDetail[]>([]);
  const [settings, setAdminSettings] = useState<SettingsResponse | null>(null);
  const [blockedDates, setBlockedDates] = useState<Set<string>>(new Set());
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Settings edit state
  const [isBookingEnabled, setIsBookingEnabled] = useState(true);
  const [startTime, setStartTime] = useState('21:00');
  const [endTime, setEndTime] = useState('23:59');
  const [availableDays, setAvailableDays] = useState<number[]>([1,2,3,4,5,6,0]);
  const [savingSettings, setSavingSettings] = useState(false);
  const [cancellingBulk, setCancellingBulk] = useState(false);
  
  // Calendar state
  const [calMonth, setCalMonth] = useState(() => {
    const d = new Date();
    return { year: d.getFullYear(), month: d.getMonth() };
  });

  const fetchData = useCallback(async (authToken: string) => {
    setLoading(true);
    setError('');
    
    try {
      // Fetch bookings
      const filter = statusFilter !== 'all' ? { status: statusFilter } : undefined;
      const bData = await getAdminBookings(authToken, filter);
      setBookings(bData.bookings);
      
      // Fetch settings
      const sData = await getAdminSettings(authToken);
      setAdminSettings(sData);
      setIsBookingEnabled(sData.is_booking_enabled);
      setStartTime(sData.daily_start_time.substring(0, 5));
      setEndTime(sData.daily_end_time.substring(0, 5));
      setAvailableDays(sData.available_days || [1,2,3,4,5,6,0]);
      
      // Fetch availability (for calendar blocked dates)
      const aData = await getAvailability(authToken);
      const blocked = new Set<string>();
      aData.availability.forEach((record: AvailabilityRecord) => {
        if (!record.is_available) blocked.add(record.date);
      });
      setBlockedDates(blocked);
      
    } catch (e: unknown) {
      if (e instanceof Error && (e.message.includes('Not authorized') || e.message.includes('token'))) {
        localStorage.removeItem('admin_token');
        router.push('/admin');
      } else {
        setError(e instanceof Error ? e.message : 'Error fetching data');
      }
    } finally {
      setLoading(false);
    }
  }, [statusFilter, router]);

  useEffect(() => {
    const t = localStorage.getItem('admin_token');
    if (!t) {
      router.push('/admin');
      return;
    }
    setToken(t);
    fetchData(t);
  }, [statusFilter, fetchData, router]);

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    router.push('/admin');
  };

  const handleCancelBooking = async (id: string) => {
    if (!confirm('Are you sure you want to cancel this booking? This will send an email to the user.')) return;
    
    try {
      await deleteAdminBooking(token, id);
      fetchData(token);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Failed to cancel');
    }
  };

  const handlePermanentDelete = async (id: string) => {
    if (!confirm('WARNING: Are you sure you want to PERMANENTLY DELETE this booking from the database? This action cannot be undone.')) return;
    
    try {
      await permanentlyDeleteAdminBooking(token, id);
      fetchData(token);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Failed to delete');
    }
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      await updateAdminSettings(token, {
        is_booking_enabled: isBookingEnabled,
        daily_start_time: startTime + ":00",
        daily_end_time: endTime + ":59",
        available_days: availableDays,
      });
      alert('Settings saved!');
      fetchData(token);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Failed to save settings');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleBulkCancel = async () => {
    if (!confirm('WARNING: Are you sure you want to cancel ALL upcoming scheduled meetings? This will immediately send emails to everyone.')) return;
    
    setCancellingBulk(true);
    try {
      const res = await bulkCancelAdminBookings(token);
      alert(res.message);
      fetchData(token);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Failed to bulk cancel');
    } finally {
      setCancellingBulk(false);
    }
  };

  const toggleDateBlock = async (dateStr: string) => {
    const isCurrentlyBlocked = blockedDates.has(dateStr);
    const newStatus = isCurrentlyBlocked; // If blocked, set available (true); if available, set blocked (false)
    
    try {
      await setAvailability(token, dateStr, newStatus);
      // Optimistic update
      setBlockedDates(prev => {
        const next = new Set(prev);
        if (newStatus) next.delete(dateStr);
        else next.add(dateStr);
        return next;
      });
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Failed to update date');
    }
  };

  // Calendar helpers
  const getDaysInMonth = (y: number, m: number) => new Date(y, m + 1, 0).getDate();
  const getFirstDayOfMonth = (y: number, m: number) => new Date(y, m, 1).getDay();
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  const formatTimePKT = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleString('en-PK', {
        timeZone: 'Asia/Karachi',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return isoStr;
    }
  };

  const getDurationLabel = (m: number) => m === 30 ? 'Project Discussion (30m)' : 'Consultation (10m)';

  if (loading && !bookings.length && !settings) {
    return (
      <div className={styles.page} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <div className={styles.topbarInner}>
          <div className={styles.logo}>
            <Sparkles size={24} />
            <span>MindFuelByAli Admin</span>
          </div>
          <div className={styles.topbarActions}>
            <button className="btn btn-ghost" onClick={() => fetchData(token)}>
              <RefreshCw size={18} /> Refresh
            </button>
            <button className="btn btn-outline" onClick={handleLogout}>
              <LogOut size={18} /> Logout
            </button>
          </div>
        </div>
      </header>

      <main className={styles.main}>
        {/* Left Col: Bookings */}
        <div className={styles.contentArea}>
          <div className="card-elevated animate-fade-in-up">
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>Bookings</h2>
                <p className={styles.sectionSubtitle}>Manage your upcoming and past meetings</p>
              </div>
              <div className={styles.filters} style={{ alignItems: 'center' }}>
                <select 
                  className={styles.filterSelect}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="all">All Statuses</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
                <button 
                  className="btn btn-sm btn-outline" 
                  style={{ color: 'var(--color-error)', borderColor: 'var(--color-error)' }}
                  onClick={handleBulkCancel}
                  disabled={cancellingBulk || bookings.filter(b => b.status === 'scheduled').length === 0}
                >
                  {cancellingBulk ? 'Cancelling...' : 'Cancel All Upcoming'}
                </button>
              </div>
            </div>

            {error && <div className="errorBanner">{error}</div>}

            <div className={styles.tableWrapper}>
              {bookings.length > 0 ? (
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Type & Time (PKT)</th>
                      <th>Topic</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bookings.map(book => {
                      const isPast = book.status === 'scheduled' && new Date(book.start_time) < new Date();
                      const status = isPast ? 'completed' : book.status;
                      
                      return (
                        <tr key={book.id} className={isPast ? styles.pastRow : ''}>
                          <td className={styles.userCell}>
                            <strong>{book.user_name}</strong>
                            <span>{book.user_email}</span>
                          </td>
                          <td>
                            <strong>{formatTimePKT(book.start_time)}</strong>
                            <br />
                            <span style={{ fontSize: '13px', color: 'var(--color-primary)' }}>
                              {getDurationLabel(book.duration)}
                            </span>
                          </td>
                          <td className={styles.topicCell}>
                            <p>{book.topic}</p>
                          </td>
                          <td>
                            <span className={`badge badge-${status}`}>
                              {status}
                            </span>
                          </td>
                          <td className={styles.actionCell}>
                            {book.status === 'scheduled' && !isPast && book.zoom_link && (
                              <a 
                                href={book.zoom_link} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="btn btn-sm btn-accent"
                                title="Join Zoom Meeting"
                              >
                                <Video size={14} /> Join
                              </a>
                            )}
                            {book.status === 'scheduled' && (
                              <button 
                                className="btn btn-sm btn-ghost" 
                                style={{ color: 'var(--color-error)' }}
                                onClick={() => handleCancelBooking(book.id)}
                                title="Cancel Meeting"
                              >
                                <XCircle size={16} />
                              </button>
                            )}
                            <button 
                              className="btn btn-sm btn-ghost" 
                              style={{ color: '#94a3b8' }}
                              onClick={() => handlePermanentDelete(book.id)}
                              title="Delete Permanently"
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div className={styles.emptyState}>
                  <Search size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
                  <p>No bookings found matching the selected filters.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Col: Settings & Calendar */}
        <div className={styles.sidebarArea}>
          
          {/* Settings Plugin */}
          <div className="card animate-fade-in-up delay-1">
            <div className={styles.sectionHeader} style={{ marginBottom: '24px' }}>
              <div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '20px' }}>Settings</h3>
                <p className={styles.sectionSubtitle}>Global controls</p>
              </div>
              <Settings size={20} style={{ color: 'var(--color-text-muted)' }} />
            </div>

            <div className={styles.settingsGroup}>
              <div className={styles.settingsRow}>
                <div>
                  <div className={styles.settingsLabel}>Accept Bookings</div>
                  <div className={styles.settingsDesc}>Turn all bookings on or off globally</div>
                </div>
                <button 
                  className={`toggle ${isBookingEnabled ? 'active' : ''}`}
                  onClick={() => setIsBookingEnabled(!isBookingEnabled)}
                />
              </div>
            </div>

            <div className={styles.settingsGroup}>
              <div className={styles.settingsLabel}>Weekly Availability Days</div>
              <div className={styles.settingsDesc}>Select which days of the week users are allowed to book.</div>
              <div className={styles.weekdayGrid}>
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, idx) => {
                  const isActive = availableDays.includes(idx);
                  return (
                    <button
                      key={day}
                      className={`${styles.weekdayBtn} ${isActive ? styles.active : ''}`}
                      onClick={() => {
                        if (isActive) {
                          setAvailableDays(availableDays.filter(d => d !== idx));
                        } else {
                          setAvailableDays([...availableDays, idx]);
                        }
                      }}
                    >
                      {day}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className={styles.settingsGroup}>
              <div className={styles.settingsLabel}>Daily Availability Windows</div>
              <div className={styles.settingsDesc}>Time slots will automatically generate between 9 PM and 12 AM PKT.</div>
              
              <div className={styles.timeInputs}>
                <input 
                  type="time" 
                  className="form-input" 
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                />
                <span>to</span>
                <input 
                  type="time" 
                  className="form-input" 
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                />
              </div>

              <button 
                className={`${styles.saveBtn} btn btn-primary`}
                onClick={handleSaveSettings}
                disabled={savingSettings}
              >
                {savingSettings ? <div className="spinner" style={{ width: '16px', height: '16px', borderTopColor: 'white' }} /> : <><Save size={16}/> Save Settings</>}
              </button>
            </div>
          </div>

          {/* Date Blocker Calendar */}
          <div className="card animate-fade-in-up delay-2">
            <div className={styles.sectionHeader} style={{ marginBottom: '20px' }}>
              <div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '20px' }}>Block Dates</h3>
                <p className={styles.sectionSubtitle}>Click a date to toggle availability</p>
              </div>
              <CalendarIcon size={20} style={{ color: 'var(--color-text-muted)' }} />
            </div>

            <div className={styles.adminCalendar}>
              <div className={styles.calHeader}>
                <button className={styles.calNav} onClick={() => setCalMonth(p => p.month === 0 ? {year: p.year-1, month: 11} : {...p, month: p.month-1})}>
                  <ChevronLeft size={16}/>
                </button>
                <h4>{monthNames[calMonth.month]} {calMonth.year}</h4>
                <button className={styles.calNav} onClick={() => setCalMonth(p => p.month === 11 ? {year: p.year+1, month: 0} : {...p, month: p.month+1})}>
                  <ChevronRight size={16}/>
                </button>
              </div>
              
              <div className={styles.calGrid}>
                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
                  <div key={i} className={styles.calDayName}>{d}</div>
                ))}
                
                {Array.from({ length: getFirstDayOfMonth(calMonth.year, calMonth.month) }).map((_, i) => (
                  <div key={`emp-${i}`} className={styles.calDayEmpty} />
                ))}
                
                {Array.from({ length: getDaysInMonth(calMonth.year, calMonth.month) }).map((_, i) => {
                  const d = i + 1;
                  const dateStr = `${calMonth.year}-${String(calMonth.month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
                  const isBlocked = blockedDates.has(dateStr);
                  
                  return (
                    <button 
                      key={d}
                      className={`${styles.calDay} ${isBlocked ? styles.calDayBlocked : ''}`}
                      onClick={() => toggleDateBlock(dateStr)}
                      title={isBlocked ? "Unblock this date" : "Block this date"}
                    >
                      {d}
                    </button>
                  );
                })}
              </div>

              <div className={styles.blockedLegend}>
                <div className={styles.blockedDot} />
                <span>Blocked / Unavailable</span>
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
