import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings, TZ_PKT
from datetime import datetime
import pytz

def _format_time_pkt(utc_time_str: str) -> str:
    """Convert UTC timestamp string to formatted PKT time."""
    try:
        dt = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
        pkt_time = dt.astimezone(TZ_PKT)
        return pkt_time.strftime("%B %d, %Y at %I:%M %p PKT")
    except Exception:
        return utc_time_str

def _booking_type_label(booking_type: str) -> str:
    """Human-readable booking type."""
    if booking_type == "project_discussion":
        return "Project Discussion (30 min)"
    return "Consultation (10 min)"

def _build_confirmation_html(
    name: str,
    booking_type: str,
    start_time: str,
    zoom_link: str,
    topic: str,
) -> str:
    """Build premium styled HTML for booking confirmation email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f7fa; color: #334155; line-height: 1.6; margin: 0; padding: 0; }}
            .wrapper {{ width: 100%; background-color: #f4f7fa; padding: 40px 0; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
            .header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 60px 40px; text-align: center; }}
            .logo-text {{ color: #ffffff; font-size: 28px; font-weight: 800; letter-spacing: -0.5px; margin: 0; }}
            .status-badge {{ display: inline-block; background: rgba(16, 185, 129, 0.1); color: #10b981; padding: 6px 16px; border-radius: 50px; font-size: 13px; font-weight: 700; margin-top: 15px; border: 1px solid rgba(16, 185, 129, 0.2); }}
            .content {{ padding: 40px; }}
            .greeting {{ font-size: 22px; font-weight: 700; color: #1e293b; margin-bottom: 20px; }}
            .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; margin: 24px 0; }}
            .info-row {{ display: flex; align-items: center; margin-bottom: 12px; }}
            .info-row:last-child {{ margin-bottom: 0; }}
            .info-label {{ font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; width: 100px; }}
            .info-value {{ font-size: 15px; color: #1e293b; font-weight: 600; flex: 1; }}
            .topic-section {{ border-top: 1px solid #e2e8f0; padding-top: 20px; margin-top: 20px; }}
            .topic-title {{ font-size: 13px; font-weight: 700; color: #64748b; margin-bottom: 8px; }}
            .topic-content {{ font-style: italic; color: #475569; }}
            .zoom-button {{ display: block; text-align: center; background: #5B4FFA; color: #ffffff !important; text-decoration: none; padding: 18px 30px; border-radius: 12px; font-weight: 700; font-size: 16px; margin: 30px 0; box-shadow: 0 4px 12px rgba(91, 79, 250, 0.3); transition: all 0.3s ease; }}
            .footer {{ background: #f8fafc; padding: 30px; text-align: center; font-size: 13px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
            .footer-links {{ margin-top: 15px; }}
            .footer-links a {{ color: #5B4FFA; text-decoration: none; margin: 0 10px; }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="header">
                    <div class="logo-text">MindFuelByAli</div>
                    <div class="status-badge">BOOKING CONFIRMED</div>
                </div>
                <div class="content">
                    <div class="greeting">Hi {name},</div>
                    <p>I'm looking forward to our session! Your meeting has been successfully scheduled. Here are the details:</p>
                    
                    <div class="card">
                        <div class="info-row">
                            <span class="info-label">Meeting</span>
                            <span class="info-value">{_booking_type_label(booking_type)}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Date/Time</span>
                            <span class="info-value">{_format_time_pkt(start_time)}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Cost</span>
                            <span class="info-value" style="color: #10b981;">100% Free</span>
                        </div>
                        
                        <div class="topic-section">
                            <div class="topic-title">YOUR DISCUSSION TOPIC</div>
                            <div class="topic-content">"{topic}"</div>
                        </div>
                    </div>

                    <a href="{zoom_link}" class="zoom-button">Join Zoom Meeting</a>

                    <p style="font-size: 14px; text-align: center; color: #64748b;">
                        Please make sure to join 2-3 minutes before the scheduled time. 
                        If you have any questions, feel free to reach out.
                    </p>
                </div>
                <div class="footer">
                    <strong>MindFuelByAli</strong><br>
                    Empowering Tech Minds with Expert Guidance<br>
                    <div class="footer-links">
                        <a href="{get_settings().frontend_url}">Visit Website</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

def _build_admin_notification_html(
    user_name: str,
    user_email: str,
    booking_type: str,
    duration: int,
    start_time: str,
    topic: str,
    zoom_link: str,
) -> str:
    """Build premium styled HTML for admin notification email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Inter', sans-serif; background-color: #0f172a; color: #94a3b8; line-height: 1.6; padding: 40px 0; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 20px; border: 1px solid #334155; overflow: hidden; }}
            .header {{ background: #334155; padding: 40px; text-align: center; border-bottom: 1px solid #475569; }}
            .logo-text {{ color: #ffffff; font-size: 20px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; }}
            .content {{ padding: 40px; }}
            .title {{ color: #ffffff; font-size: 24px; font-weight: 800; margin-bottom: 10px; }}
            .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 25px 0; }}
            .stat-box {{ background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #334155; }}
            .stat-label {{ font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 5px; }}
            .stat-value {{ color: #f8fafc; font-size: 16px; font-weight: 600; }}
            .user-card {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 25px; border-radius: 15px; border: 1px solid #334155; margin: 20px 0; }}
            .user-name {{ color: #ffffff; font-size: 18px; font-weight: 700; }}
            .user-email {{ color: #5B4FFA; font-size: 14px; font-weight: 600; }}
            .topic-box {{ background: #0f172a; padding: 20px; border-radius: 12px; border-left: 4px solid #5B4FFA; margin-top: 20px; }}
            .topic-label {{ font-size: 12px; font-weight: 800; color: #64748b; margin-bottom: 10px; }}
            .link-box {{ margin-top: 30px; text-align: center; }}
            .btn {{ display: inline-block; background: #ffffff; color: #1e293b !important; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 700; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo-text">MindFuel Admin</div>
            </div>
            <div class="content">
                <div class="title">New Session Booked</div>
                <p>You have a new meeting scheduled through the platform.</p>
                
                <div class="user-card">
                    <div class="user-name">{user_name}</div>
                    <div class="user-email">{user_email}</div>
                </div>

                <div class="stat-grid">
                    <div class="stat-box">
                        <div class="stat-label">Type</div>
                        <div class="stat-value">{_booking_type_label(booking_type)}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Duration</div>
                        <div class="stat-value">{duration} Minutes</div>
                    </div>
                </div>

                <div class="stat-box" style="margin-bottom: 20px;">
                    <div class="stat-label">Date & Time (PKT)</div>
                    <div class="stat-value" style="color: #10b981;">{_format_time_pkt(start_time)}</div>
                </div>

                <div class="topic-box">
                    <div class="topic-label">DISCUSSION TOPIC</div>
                    <div style="color: #f8fafc; font-style: italic;">"{topic}"</div>
                </div>

                <div class="link-box">
                    <a href="{zoom_link}" class="btn">Launch Zoom Meeting</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

def _build_cancellation_html(name: str, booking_type: str, start_time: str) -> str:
    """Build premium styled HTML for cancellation/apology email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Inter', sans-serif; background-color: #fff1f2; color: #475569; line-height: 1.6; padding: 40px 0; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 20px; border: 1px solid #fecaca; overflow: hidden; box-shadow: 0 10px 25px rgba(225, 29, 72, 0.05); }}
            .header {{ background: #f43f5e; padding: 50px 40px; text-align: center; }}
            .logo-text {{ color: #ffffff; font-size: 24px; font-weight: 800; }}
            .content {{ padding: 40px; }}
            .title {{ font-size: 24px; font-weight: 800; color: #e11d48; margin-bottom: 15px; }}
            .reason-box {{ background: #fff1f2; border: 1px solid #ffe4e6; border-radius: 12px; padding: 20px; margin: 25px 0; text-align: center; }}
            .meeting-info {{ font-weight: 700; color: #475569; }}
            .footer {{ padding: 30px; text-align: center; font-size: 13px; color: #94a3b8; border-top: 1px solid #f1f5f9; }}
            .btn {{ display: inline-block; background: #1e293b; color: #ffffff !important; text-decoration: none; padding: 15px 30px; border-radius: 12px; font-weight: 700; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo-text">MindFuelByAli</div>
            </div>
            <div class="content">
                <div class="title">Meeting Cancelled</div>
                <p>Hi {name},</p>
                <p>We are writing to inform you that your upcoming session has been cancelled. We sincerely apologize for any disruption this may cause to your schedule.</p>
                
                <div class="reason-box">
                    <div style="font-size: 12px; text-transform: uppercase; color: #f43f5e; font-weight: 800; margin-bottom: 5px;">Cancelled Session</div>
                    <div class="meeting-info">{_booking_type_label(booking_type)}</div>
                    <div class="meeting-info" style="color: #94a3b8; font-weight: 500;">{_format_time_pkt(start_time)}</div>
                </div>

                <p>You can reschedule your appointment at any time using the link below:</p>
                <center>
                    <a href="{get_settings().frontend_url}" class="btn">Reschedule Now</a>
                </center>
            </div>
            <div class="footer">
                We value your time and hope to see you soon.<br>
                <strong>MindFuelByAli Support Team</strong>
            </div>
        </div>
    </body>
    </html>
    """

import resend

def _send_email_sync(to_email: str, subject: str, html_content: str) -> bool:
    """Synchronous core for sending email via Resend API."""
    settings = get_settings()
    
    if settings.resend_api_key == "re_placeholder_key":
        print(f"[MOCK EMAIL] To: {to_email} | Subject: {subject}")
        return True

    resend.api_key = settings.resend_api_key

    try:
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": to_email,
            "subject": subject,
            "html": html_content
        })
        return True
    except Exception as e:
        print(f"[RESEND ERROR] {e}")
        return False

async def send_booking_confirmation(
    user_email: str,
    user_name: str,
    booking_type: str,
    start_time: str,
    zoom_link: str,
    topic: str,
) -> bool:
    """Send booking confirmation email to user."""
    subject = f"✅ Meeting Confirmed — {_booking_type_label(booking_type)}"
    html = _build_confirmation_html(user_name, booking_type, start_time, zoom_link, topic)
    
    return await asyncio.to_thread(_send_email_sync, user_email, subject, html)

async def send_admin_notification(
    user_name: str,
    user_email: str,
    booking_type: str,
    duration: int,
    start_time: str,
    topic: str,
    zoom_link: str,
) -> bool:
    """Send booking notification email to admin."""
    settings = get_settings()
    subject = f"📅 New Booking: {user_name} — {_booking_type_label(booking_type)}"
    html = _build_admin_notification_html(
        user_name, user_email, booking_type, duration, start_time, topic, zoom_link
    )
    
    return await asyncio.to_thread(_send_email_sync, settings.admin_email, subject, html)

async def send_cancellation_email(
    user_email: str,
    user_name: str,
    booking_type: str,
    start_time: str,
) -> bool:
    """Send cancellation email to user."""
    subject = "❌ Meeting Cancelled — MindFuelByAli"
    html = _build_cancellation_html(user_name, booking_type, start_time)
    
    return await asyncio.to_thread(_send_email_sync, user_email, subject, html)
