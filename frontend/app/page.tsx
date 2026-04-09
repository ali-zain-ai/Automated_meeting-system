'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Image from 'next/image';
import { getSlots, createBooking, Slot, BookingResponse } from '@/lib/api';
import {
  Clock,
  MessageSquare,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Video,
  Zap,
  Brain,
  User,
  Mail,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
} from 'lucide-react';
import styles from './page.module.css';

type BookingType = 'consultation' | 'project_discussion';
type Step = 'type' | 'date' | 'time' | 'form' | 'confirm';

const containerVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { 
      duration: 0.6, 
      staggerChildren: 0.1 
    }
  },
  exit: { 
    opacity: 0, 
    y: -20,
    transition: { duration: 0.3 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.5 }
  }
};

export default function BookingPage() {
  const [step, setStep] = useState<Step>('type');
  const [bookingType, setBookingType] = useState<BookingType | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [selectedSlot, setSelectedSlot] = useState<string>('');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [topic, setTopic] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [booking, setBooking] = useState<BookingResponse | null>(null);

  const [calendarMonth, setCalendarMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  useEffect(() => {
    if (!selectedDate) return;
    setLoadingSlots(true);
    setError('');
    getSlots(selectedDate)
      .then((data) => setSlots(data.slots))
      .catch((e) => {
        setError(e.message);
        setSlots([]);
      })
      .finally(() => setLoadingSlots(false));
  }, [selectedDate]);

  const handleBookingTypeSelect = (type: BookingType) => {
    setBookingType(type);
    setStep('date');
  };

  const handleDateSelect = (dateStr: string) => {
    setSelectedDate(dateStr);
    setSelectedSlot('');
    setStep('time');
  };

  const handleSlotSelect = (slot: string) => {
    setSelectedSlot(slot);
    setStep('form');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bookingType || !selectedDate || !selectedSlot) return;

    setSubmitting(true);
    setError('');

    try {
      const result = await createBooking({
        name,
        email,
        booking_type: bookingType,
        date: selectedDate,
        start_time: selectedSlot,
        topic,
      });
      setBooking(result);
      setStep('confirm');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create booking');
    } finally {
      setSubmitting(false);
    }
  };

  const goBack = () => {
    const steps: Step[] = ['type', 'date', 'time', 'form'];
    const idx = steps.indexOf(step);
    if (idx > 0) setStep(steps[idx - 1]);
  };

  const resetBooking = () => {
    setStep('type');
    setBookingType(null);
    setSelectedDate('');
    setSelectedSlot('');
    setSlots([]);
    setName('');
    setEmail('');
    setTopic('');
    setBooking(null);
    setError('');
  };

  const getDaysInMonth = (y: number, m: number) => new Date(y, m + 1, 0).getDate();
  const getFirstDayOfMonth = (y: number, m: number) => new Date(y, m, 1).getDay();
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  const navigateMonth = (delta: number) => {
    setCalendarMonth((prev) => {
      let m = prev.month + delta;
      let y = prev.year;
      if (m < 0) { m = 11; y--; }
      if (m > 11) { m = 0; y++; }
      return { year: y, month: m };
    });
  };

  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  const getBookingTypeLabel = (type: BookingType) =>
    type === 'project_discussion' ? 'Project Discussion' : 'Consultation';

  const getDurationLabel = (type: BookingType) =>
    type === 'project_discussion' ? '30 minutes' : '10 minutes';

  const formatTime12Hour = (time24: string) => {
    if (!time24) return '';
    const [hours, minutes] = time24.split(':').map(Number);
    const period = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    return `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;
  };

  const formatTimePKT = (isoStr: string) => {
    try {
      return new Date(isoStr).toLocaleString('en-PK', {
        timeZone: 'Asia/Karachi',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.logo}>
            <div className={styles.logoImage}>
              <Image src="/logo.jpg" alt="MindFuelByAli" width={40} height={40} priority />
            </div>
            <span>MindFuelByAli</span>
          </div>
          <span className="badge badge-free">100% Free</span>
        </div>
      </header>

      {/* Progress Indicator */}
      {step !== 'confirm' && (
        <div className={styles.progressBar}>
          <div className={styles.progressTrack}>
            <motion.div
              className={styles.progressFill}
              initial={{ width: 0 }}
              animate={{ 
                width: step === 'type' ? '25%' : step === 'date' ? '50%' : step === 'time' ? '75%' : '100%' 
              }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
          <div className={styles.progressSteps}>
            {['Choose Type', 'Pick Date', 'Select Time', 'Details'].map((label, i) => {
              const stepOrder: Step[] = ['type', 'date', 'time', 'form'];
              const isActive = stepOrder.indexOf(step) >= i;
              return (
                <span key={label} className={`${styles.progressStep} ${isActive ? styles.progressStepActive : ''}`}>
                  {label}
                </span>
              );
            })}
          </div>
        </div>
      )}

      <main className={styles.main}>
        <AnimatePresence mode="wait">
          {/* STEP 1: TYPE */}
          {step === 'type' && (
            <motion.div
              key="step-type"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className={styles.stepContent}
            >
               <section className={styles.hero}>
                <div className={styles.heroBadge}>
                  <div className={styles.heroBadgeIcon}>
                    <Image src="/logo.jpg" alt="Icon" width={20} height={20} />
                  </div>
                  <span>AI & ML Expert Consultations</span>
                </div>
                <h1 className={styles.heroTitle}>
                  Book a Free<br />
                  <span className={styles.heroGradient}>Guidance Session</span>
                </h1>
                <p className={styles.heroDesc}>
                  Expert advice on career, architecture, or technical blockers.
                </p>
              </section>

              <h2 className={styles.stepTitle}>Choose Session</h2>
              <div className={styles.typeCards}>
                <motion.button
                  variants={itemVariants}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={styles.typeCard}
                  onClick={() => handleBookingTypeSelect('consultation')}
                >
                  <div className={styles.typeCardIcon}><Zap /></div>
                  <h3>Quick Consultation</h3>
                  <span className={styles.typeDuration}>10 minutes</span>
                  <p className={styles.typeDesc}>Quick technical queries or career guidance.</p>
                  <div className={styles.typeCardAction}>Select <ArrowRight size={16} /></div>
                </motion.button>

                <motion.button
                  variants={itemVariants}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={styles.typeCard}
                  onClick={() => handleBookingTypeSelect('project_discussion')}
                >
                  <div className={`${styles.typeCardIcon} ${styles.typeCardIconAccent}`}><MessageSquare /></div>
                  <h3>Project Discussion</h3>
                  <span className={styles.typeDuration}>30 minutes</span>
                  <p className={styles.typeDesc}>In-depth architecture review or project help.</p>
                  <div className={styles.typeCardAction}>Select <ArrowRight size={16} /></div>
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* STEP 2: DATE */}
          {step === 'date' && (
            <motion.div
              key="step-date"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className={styles.stepContent}
            >
              <button className={styles.backBtn} onClick={goBack}><ArrowLeft size={16} /> Back</button>
              <h2 className={styles.stepTitle}>Pick a Date</h2>
              <p className={styles.stepSubtitle}>{getBookingTypeLabel(bookingType!)} — {getDurationLabel(bookingType!)}</p>

              <div className={styles.calendar}>
                <div className={styles.calendarHeader}>
                  <button className={styles.calendarNav} onClick={() => navigateMonth(-1)}><ChevronLeft /></button>
                  <h3 className={styles.calendarMonth}>{monthNames[calendarMonth.month]} {calendarMonth.year}</h3>
                  <button className={styles.calendarNav} onClick={() => navigateMonth(1)}><ChevronRight /></button>
                </div>
                <div className={styles.calendarGrid}>
                  {['S','M','T','W','T','F','S'].map((d, i) => <div key={`${d}-${i}`} style={{textAlign:'center', fontSize:12, fontWeight:800, color:'#94a3b8'}}>{d}</div>)}
                  {Array.from({ length: getFirstDayOfMonth(calendarMonth.year, calendarMonth.month) }).map((_, i) => <div key={`empty-${i}`} />)}
                  {Array.from({ length: getDaysInMonth(calendarMonth.year, calendarMonth.month) }).map((_, i) => {
                    const d = i + 1;
                    const dateStr = `${calendarMonth.year}-${String(calendarMonth.month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
                    const isPast = dateStr < todayStr;
                    return (
                      <button
                        key={d}
                        className={`${styles.calendarDay} ${dateStr === selectedDate ? styles.calendarDaySelected : ''} ${dateStr === todayStr ? styles.calendarDayToday : ''}`}
                        disabled={isPast}
                        onClick={() => handleDateSelect(dateStr)}
                      >
                        {d}
                      </button>
                    );
                  })}
                </div>
              </div>
            </motion.div>
          )}

          {/* STEP 3: TIME */}
          {step === 'time' && (
            <motion.div
              key="step-time"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className={styles.stepContent}
            >
              <button className={styles.backBtn} onClick={goBack}><ArrowLeft size={16} /> Back</button>
              <h2 className={styles.stepTitle}>Select Time</h2>
              <p className={styles.stepSubtitle}><CalendarIcon size={14} style={{display:'inline', verticalAlign:'middle'}} /> {selectedDate} (PKT)</p>

              {loadingSlots ? (
                <div className={styles.slotsLoading}><div className="spinner" /><p>Finding available slots...</p></div>
              ) : slots.length === 0 ? (
                <div className={styles.noSlots}><p>No slots available. Try another date.</p></div>
              ) : (
                <div className={styles.slotsGrid}>
                  {slots.map((slot, i) => (
                    <motion.button
                      key={slot.start}
                      variants={itemVariants}
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      className={`${styles.slotPill} ${!slot.available ? styles.slotPillDisabled : ''} ${selectedSlot === slot.start ? styles.slotPillSelected : ''}`}
                      disabled={!slot.available}
                      onClick={() => handleSlotSelect(slot.start)}
                    >
                      <Clock size={14} /> {formatTime12Hour(slot.start)}
                    </motion.button>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* STEP 4: FORM */}
          {step === 'form' && (
            <motion.div
              key="step-form"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className={styles.stepContent}
            >
              <button className={styles.backBtn} onClick={goBack}><ArrowLeft size={16} /> Back</button>
              <h2 className={styles.stepTitle}>Your Details</h2>
              
              <div className={styles.summaryCard}>
                <div className={styles.summaryRow}><span>Date & Time</span><strong>{selectedDate} @ {formatTime12Hour(selectedSlot)}</strong></div>
                <div className={styles.summaryRow}><span>Cost</span><strong style={{color:'var(--color-accent)'}}>FREE ✨</strong></div>
              </div>

              <form onSubmit={handleSubmit} className={styles.bookingForm}>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Full Name</label>
                  <div className={styles.inputWrapper}>
                    <User className={styles.inputIcon} size={18} />
                    <input className={styles.formInput} placeholder="Ali Raza" value={name} onChange={e => setName(e.target.value)} required />
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Email Address</label>
                  <div className={styles.inputWrapper}>
                    <Mail className={styles.inputIcon} size={18} />
                    <input className={styles.formInput} type="email" placeholder="ali@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
                  </div>
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Discussion Topic</label>
                  <div className={styles.inputWrapper}>
                    <MessageSquare className={styles.inputIcon} style={{ top: '16px' }} size={18} />
                    <textarea 
                      className={styles.formInput} 
                      style={{ resize: 'none', height: 120, paddingTop: 14 }} 
                      placeholder="What's on your mind? (Any specific questions or goals?)" 
                      value={topic} 
                      onChange={e => setTopic(e.target.value)} 
                      required 
                      maxLength={300} 
                    />
                  </div>
                  <span className={styles.charCount}>{topic.length} / 300</span>
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '16px' }} disabled={submitting}>
                  {submitting ? <div className="spinner" /> : <><Video size={20} /> Confirm Meeting Request</>}
                </button>
              </form>
            </motion.div>
          )}

          {/* STEP 5: CONFIRM */}
          {step === 'confirm' && booking && (
            <motion.div
              key="step-confirm"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', damping: 12 }}
              className={styles.confirmSection}
            >
              <div className={styles.confirmCard}>
                <div className={styles.confirmIcon}><CheckCircle2 size={80} /></div>
                <h2 className={styles.confirmTitle}>Confirmed! 🎉</h2>
                <p className={styles.confirmSubtitle}>Details sent to your email.</p>
                <div className={styles.confirmDetails} style={{textAlign:'left'}}>
                   <div className={styles.confirmDetail}><span>Meeting</span><strong>{getBookingTypeLabel(bookingType!)}</strong></div>
                   <div className={styles.confirmDetail}><span>Starts</span><strong>{formatTimePKT(booking.start_time)}</strong></div>
                </div>
                <a href={booking.zoom_link} target="_blank" rel="noreferrer" className="btn btn-accent btn-lg" style={{width:'100%', marginBottom:20}}>
                  <Video size={20} /> Join Meeting <ExternalLink size={16} />
                </a>
                <button className="btn btn-ghost" onClick={resetBooking}>Book Another</button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className={styles.footer}>
        <p>© {new Date().getFullYear()} MindFuelByAli — All sessions are 100% Free</p>
      </footer>
    </div>
  );
}
