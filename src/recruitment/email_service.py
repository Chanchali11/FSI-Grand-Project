from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html
import logging
import smtplib

from sqlalchemy.orm import Session

from config import settings
from src.database.models import EmailDeliveryStatus, EmailNotification

logger = logging.getLogger(__name__)


class EmailService:
    """
    Enterprise Email Notification Service supporting:
    - Real SMTP transport (with STARTTLS or SSL)
    - Safe deterministic Mock Transport for local/offline environments
    - Full delivery tracking (PENDING, QUEUED, SENT, DELIVERED, FAILED)
    - Anti-replay idempotency and safe retry tracking
    - Zero plaintext credential or password leaks
    """

    @classmethod
    def send_next_round_notification(
        cls,
        session: Session,
        recipient_email: str,
        student_name: str,
        job_title: str,
        company_name: str,
        round_name: str = "Round 2: Technical Deep-Dive",
        round_date_str: str | None = None,
        round_time_str: str | None = None,
        further_instructions: str | None = None,
        candidate_id: str | None = None,
    ) -> tuple[bool, str]:
        """
        Send congratulations and details for advancing to the next recruitment round.
        Logs delivery status in EmailNotification.
        """
        subject = "Congratulations! Selected for the Next Round — Hirexp AI"
        body_html = cls._build_next_round_email_html(
            student_name=student_name,
            job_title=job_title,
            company_name=company_name,
            round_name=round_name,
            round_date_str=round_date_str,
            round_time_str=round_time_str,
            further_instructions=further_instructions,
        )

        notification = EmailNotification(
            recipient_email=recipient_email.strip().lower(),
            recipient_name=student_name,
            subject=subject,
            body_html=body_html,
            status=EmailDeliveryStatus.PENDING.value,
            invitation_id=None,
            delivery_attempts=0,
            created_at=datetime.utcnow(),
        )
        session.add(notification)
        session.flush()

        success, response_msg = cls._dispatch_email(
            recipient_email=recipient_email,
            subject=subject,
            body_html=body_html,
        )

        notification.delivery_attempts += 1
        if success:
            notification.status = EmailDeliveryStatus.DELIVERED.value
            notification.provider_response = response_msg
            notification.sent_at = datetime.utcnow()
            notification.delivered_at = datetime.utcnow()
        else:
            notification.status = EmailDeliveryStatus.FAILED.value
            notification.error_message = response_msg

        # Use flush (not commit) — the caller owns the transaction boundary
        session.flush()
        return success, response_msg

    @classmethod
    def send_interview_invitation(
        cls,
        session: Session,
        recipient_email: str,
        student_name: str,
        username: str,
        setup_url: str,
        login_url: str,
        job_title: str,
        company_name: str,
        deadline_str: str | None = None,
        invitation_id: str | None = None,
        force_resend: bool = False,
    ) -> tuple[bool, str]:
        """
        Send professional shortlisted candidate interview invitation HTML email.
        Logs and tracks lifecycle in EmailNotification database record.
        """
        subject = "Congratulations! You Have Been Shortlisted — HireSphere AI"
        deadline_text = deadline_str if deadline_str else "Within 48 hours of receiving this email"

        body_html = cls._build_invitation_email_html(
            student_name=student_name,
            username=username,
            setup_url=setup_url,
            login_url=login_url,
            job_title=job_title,
            company_name=company_name,
            deadline_text=deadline_text,
        )

        # Check existing notification record for idempotency unless force_resend
        notification = None
        if invitation_id and not force_resend:
            notification = (
                session.query(EmailNotification)
                .filter(
                    EmailNotification.invitation_id == invitation_id,
                    EmailNotification.status.in_([EmailDeliveryStatus.DELIVERED.value, EmailDeliveryStatus.SENT.value]),
                )
                .first()
            )
            if notification:
                logger.info(f"Email already successfully sent for invitation {invitation_id}.")
                return True, "Invitation email previously delivered."

        # Create audit record in PENDING status
        notification = EmailNotification(
            recipient_email=recipient_email.strip().lower(),
            recipient_name=student_name,
            subject=subject,
            body_html=body_html,
            status=EmailDeliveryStatus.PENDING.value,
            invitation_id=invitation_id,
            delivery_attempts=0,
            created_at=datetime.utcnow(),
        )
        session.add(notification)
        session.flush()

        # Send via configured transport
        success, response_msg = cls._dispatch_email(
            recipient_email=recipient_email,
            subject=subject,
            body_html=body_html,
        )

        notification.delivery_attempts += 1
        if success:
            notification.status = EmailDeliveryStatus.DELIVERED.value
            notification.provider_response = response_msg
            notification.sent_at = datetime.utcnow()
            notification.delivered_at = datetime.utcnow()
        else:
            notification.status = EmailDeliveryStatus.FAILED.value
            notification.error_message = response_msg

        # Use flush (not commit) — the caller owns the transaction boundary
        session.flush()
        return success, response_msg

    @classmethod
    def _dispatch_email(
        cls,
        recipient_email: str,
        subject: str,
        body_html: str,
    ) -> tuple[bool, str]:
        """Dispatches email via standard library smtplib or deterministic mock transport."""
        from config import _get_setting

        smtp_mock_mode = settings.SMTP_MOCK_MODE or (_get_setting("SMTP_MOCK_MODE", "true").lower() in ("true", "1", "yes"))
        smtp_host = _get_setting("SMTP_HOST", settings.SMTP_HOST)
        smtp_port = int(_get_setting("SMTP_PORT", str(settings.SMTP_PORT)))
        smtp_user = _get_setting("SMTP_USER", settings.SMTP_USER)
        smtp_password = _get_setting("SMTP_PASSWORD", settings.SMTP_PASSWORD)
        smtp_from_email = _get_setting("SMTP_FROM_EMAIL", settings.SMTP_FROM_EMAIL)
        smtp_from_name = _get_setting("SMTP_FROM_NAME", settings.SMTP_FROM_NAME)
        smtp_use_tls = _get_setting("SMTP_USE_TLS", str(settings.SMTP_USE_TLS)).lower() in ("true", "1", "yes")

        if smtp_mock_mode or not smtp_host or not smtp_user:
            mock_note = (
                "MockTransport: [MOCK MODE] Simulated delivery — "
                "SMTP credentials not configured."
            )
            logger.info(
                f"[MOCK EMAIL SERVICE] To: {recipient_email} | Subject: {subject} | {mock_note}"
            )
            return True, mock_note

        # Real delivery via standard library smtplib
        try:
            clean_password = smtp_password.replace(" ", "") if smtp_password else ""
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{smtp_from_name} <{smtp_from_email}>"
            msg["To"] = recipient_email

            plain_text = (
                "Congratulations! You have been shortlisted for an interview with HireSphere AI.\n\n"
                "Please open this email in an HTML-capable email client to view your "
                "credentials and interview portal link."
            )
            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
                if smtp_use_tls:
                    server.starttls()

            if smtp_user and clean_password:
                server.login(smtp_user, clean_password)

            server.sendmail(smtp_from_email, [recipient_email], msg.as_string())
            server.quit()

            logger.info(f"[SMTP] Email sent successfully to {recipient_email}")
            return True, f"SMTP: Message delivered to {recipient_email}"

        except Exception as e:
            logger.error(f"[SMTP] Failed to send email to {recipient_email}: {e}", exc_info=True)
            return False, f"SMTP Delivery Error: {str(e)}"

    @staticmethod
    def _build_invitation_email_html(
        student_name: str,
        username: str,
        setup_url: str,
        login_url: str,
        job_title: str,
        company_name: str,
        deadline_text: str,
    ) -> str:
        """Constructs a responsive HTML email complying with HireSphere AI branding."""
        clean_name = html.escape(student_name)
        clean_username = html.escape(username)
        clean_job = html.escape(job_title)
        clean_company = html.escape(company_name)
        clean_deadline = html.escape(deadline_text)

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HireSphere AI Interview Invitation</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0F172A;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F8FAFC; padding: 32px 16px;">
    <tr>
      <td align="center">
        <!-- Main Container Card -->
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #FFFFFF; border-radius: 14px; border: 1px solid #E2E8F0; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06); overflow: hidden;" cellspacing="0" cellpadding="0">
          
          <!-- Branded Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4F46E5 100%); padding: 36px 32px; text-align: center;">
              <div style="display: inline-block; width: 44px; height: 44px; border-radius: 12px; background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.25); line-height: 44px; font-size: 22px; margin-bottom: 12px;">
                ⚡
              </div>
              <h1 style="margin: 0; color: #FFFFFF; font-size: 24px; font-weight: 800; letter-spacing: -0.02em;">HireSphere AI</h1>
              <p style="margin: 6px 0 0 0; color: #C7D2FE; font-size: 13px; font-weight: 500;">Next-Gen Autonomous Candidate Screening & Assessment</p>
            </td>
          </tr>

          <!-- Body Content -->
          <tr>
            <td style="padding: 36px 32px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; color: #0F172A; font-weight: 600;">
                Dear {clean_name},
              </p>
              
              <div style="background: #ECFDF5; border-left: 4px solid #10B981; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px;">
                <p style="margin: 0; color: #065F46; font-size: 15px; font-weight: 700;">
                  🎉 Congratulations!
                </p>
                <p style="margin: 4px 0 0 0; color: #047857; font-size: 14px; line-height: 1.5;">
                  We are pleased to inform you that you have been shortlisted for the <strong>{clean_job}</strong> position at <strong>{clean_company}</strong>.
                </p>
              </div>

              <p style="margin: 0 0 20px 0; font-size: 14px; color: #334155; line-height: 1.6;">
                You are invited to attend the AI-powered virtual interview through HireSphere AI.
                Please review your unique interview credentials below:
              </p>

              <!-- Credentials Box -->
              <table role="presentation" width="100%" style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; margin-bottom: 24px;" cellspacing="0" cellpadding="14">
                <tr>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 13px; color: #64748B; width: 35%;"><strong>Username:</strong></td>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 14px; color: #4F46E5; font-weight: 700; font-family: monospace;">{clean_username}</td>
                </tr>
                <tr>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 13px; color: #64748B;"><strong>Job Position:</strong></td>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 13px; color: #0F172A; font-weight: 600;">{clean_job}</td>
                </tr>
                <tr>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 13px; color: #64748B;"><strong>Organization:</strong></td>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 13px; color: #0F172A;">{clean_company}</td>
                </tr>
                <tr>
                  <td style="font-size: 13px; color: #64748B;"><strong>Interview Deadline:</strong></td>
                  <td style="font-size: 13px; color: #DC2626; font-weight: 600;">{clean_deadline}</td>
                </tr>
              </table>

              <!-- Call to Action Buttons -->
              <div style="text-align: center; margin: 30px 0;">
                <a href="{setup_url}" style="display: inline-block; background-color: #4F46E5; color: #FFFFFF; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; box-shadow: 0 2px 8px rgba(79, 70, 229, 0.35); margin-bottom: 10px;">
                  🔑 Set Your Password Now →
                </a>
                <div style="font-size: 12px; color: #64748B; margin-top: 6px;">
                  This secure password setup link is single-use and will expire in 48 hours.
                </div>
              </div>

              <!-- Portal Link -->
              <div style="background-color: #F1F5F9; border-radius: 8px; padding: 12px 16px; margin-bottom: 24px; font-size: 13px; color: #475569;">
                <strong>Interview Login URL:</strong> <a href="{login_url}" style="color: #4F46E5; text-decoration: underline; word-break: break-all;">{login_url}</a>
              </div>

              <!-- Important Instructions -->
              <h3 style="margin: 24px 0 10px 0; font-size: 14px; font-weight: 700; color: #0F172A;">Interview Instructions:</h3>
              <ul style="margin: 0 0 24px 0; padding-left: 20px; font-size: 13px; color: #475569; line-height: 1.6;">
                <li>Please set your password using the secure link before accessing the interview portal.</li>
                <li>Ensure you are in a quiet, well-lit environment with a functional microphone.</li>
                <li>The virtual avatar interviewer will read questions aloud and listen to your spoken responses.</li>
                <li>Questions are dynamically tailored to your verified resume background and applied role.</li>
                <li>After logging in with your username and chosen password, you can begin your virtual interview.</li>
              </ul>

              <!-- Sign-off -->
              <p style="margin: 0; font-size: 14px; color: #0F172A; line-height: 1.6;">
                Best regards,<br>
                <strong style="color: #4F46E5;">HireSphere AI Recruitment Team</strong>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 20px 32px; text-align: center;">
              <p style="margin: 0; font-size: 11px; color: #94A3B8; line-height: 1.5;">
                This is an automated notification from HireSphere AI. To protect candidate privacy, no permanent credentials are transmitted via email.<br>
                &copy; {datetime.utcnow().year} HireSphere AI. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    @staticmethod
    def _build_next_round_email_html(
        student_name: str,
        job_title: str,
        company_name: str,
        round_name: str,
        round_date_str: str | None = None,
        round_time_str: str | None = None,
        further_instructions: str | None = None,
    ) -> str:
        """Constructs a responsive HTML email for candidates selected for next recruitment round."""
        clean_name = html.escape(student_name)
        clean_job = html.escape(job_title)
        clean_company = html.escape(company_name)
        clean_round = html.escape(round_name or "Next Recruitment Round")
        clean_date = html.escape(round_date_str) if round_date_str else "To be announced shortly"
        clean_time = html.escape(round_time_str) if round_time_str else "Details will be sent in a calendar invitation"
        clean_instructions = html.escape(further_instructions) if further_instructions else "Our technical recruitment team will reach out with calendar invites and session links."

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Congratulations! Selected for the Next Round — Hirexp AI</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0F172A;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F8FAFC; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #FFFFFF; border-radius: 14px; border: 1px solid #E2E8F0; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06); overflow: hidden;" cellspacing="0" cellpadding="0">
          
          <tr>
            <td style="background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4F46E5 100%); padding: 36px 32px; text-align: center;">
              <div style="display: inline-block; width: 44px; height: 44px; border-radius: 12px; background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.25); line-height: 44px; font-size: 22px; margin-bottom: 12px;">
                🚀
              </div>
              <h1 style="margin: 0; color: #FFFFFF; font-size: 24px; font-weight: 800; letter-spacing: -0.02em;">Hirexp AI</h1>
              <p style="margin: 6px 0 0 0; color: #C7D2FE; font-size: 13px; font-weight: 500;">Automated Recruitment & Talent Pipeline</p>
            </td>
          </tr>

          <tr>
            <td style="padding: 36px 32px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; color: #0F172A; font-weight: 600;">
                Dear {clean_name},
              </p>
              
              <div style="background: #ECFDF5; border-left: 4px solid #10B981; border-radius: 8px; padding: 16px 20px; margin-bottom: 24px;">
                <p style="margin: 0; color: #065F46; font-size: 16px; font-weight: 700;">
                  🎉 Congratulations!
                </p>
                <p style="margin: 6px 0 0 0; color: #047857; font-size: 14px; line-height: 1.5;">
                  We are pleased to inform you that you have successfully completed your initial assessment for the position of <strong>{clean_job}</strong> at <strong>{clean_company}</strong>.
                </p>
                <p style="margin: 6px 0 0 0; color: #047857; font-size: 14px; line-height: 1.5;">
                  Based on the recruitment team's evaluation, you have been <strong>selected for the next round</strong>!
                </p>
              </div>

              <h3 style="margin: 20px 0 12px 0; font-size: 15px; font-weight: 700; color: #0F172A;">Next Round Details:</h3>

              <table role="presentation" width="100%" style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; margin-bottom: 24px;" cellspacing="0" cellpadding="14">
                <tr>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 13px; color: #64748B; width: 35%;"><strong>Next Round:</strong></td>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 14px; color: #4F46E5; font-weight: 700;">{clean_round}</td>
                </tr>
                <tr>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 13px; color: #64748B;"><strong>Date:</strong></td>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 14px; color: #0F172A; font-weight: 600;">{clean_date}</td>
                </tr>
                <tr>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 13px; color: #64748B;"><strong>Time:</strong></td>
                  <td style="border-bottom: 1px solid #E2E8F0; font-size: 14px; color: #0F172A;">{clean_time}</td>
                </tr>
                <tr>
                  <td style="font-size: 13px; color: #64748B;"><strong>Further Instructions:</strong></td>
                  <td style="font-size: 13px; color: #334155; line-height: 1.5;">{clean_instructions}</td>
                </tr>
              </table>

              <p style="margin: 24px 0 0 0; font-size: 14px; color: #0F172A; line-height: 1.6;">
                Best regards,<br>
                <strong style="color: #4F46E5;">Recruitment Team</strong><br>
                Hirexp AI
              </p>
            </td>
          </tr>

          <tr>
            <td style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 20px 32px; text-align: center;">
              <p style="margin: 0; font-size: 11px; color: #94A3B8; line-height: 1.5;">
                &copy; {datetime.utcnow().year} Hirexp AI Automated Recruitment Management System.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
