import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.app_name = os.getenv("APP_NAME", "PhD Advisory Panel")

    async def send_email_verification(self, to_email: str, verification_code: str, user_name: str = "") -> bool:
        """Send email verification with 6-digit code"""
        try:
            if not all([self.smtp_username, self.smtp_password]):
                logger.error("SMTP credentials not configured")
                return False

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Verify Your Email - {self.app_name}"
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Create HTML and text content
            greeting = f"Hi {user_name}," if user_name else "Hello,"
            
            text_content = f"""
Email Verification

{greeting}

Welcome to {self.app_name}! To complete your account setup, please verify your email address.

Your verification code is: {verification_code}

This code will expire in 30 minutes.

If you did not create an account with us, please ignore this email.

Best regards,
{self.app_name} Team
"""

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background-color: #f9fafb; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
        .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 40px 20px; text-align: center; }}
        .header h1 {{ color: #ffffff; margin: 0; font-size: 24px; }}
        .content {{ padding: 40px 20px; }}
        .code-box {{ background-color: #eff6ff; border: 2px solid #6366f1; border-radius: 12px; padding: 20px; text-align: center; margin: 20px 0; }}
        .code {{ font-size: 32px; font-weight: bold; color: #6366f1; letter-spacing: 4px; }}
        .welcome {{ background-color: #f0fdf4; border-left: 4px solid #10b981; padding: 16px; margin: 20px 0; }}
        .footer {{ background-color: #f3f4f6; padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
        .button {{ background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: 500; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {self.app_name}</h1>
        </div>
        <div class="content">
            <div class="welcome">
                <p style="margin: 0; color: #065f46; font-weight: 500;">🎉 Welcome to your PhD journey!</p>
            </div>
            
            <p>{greeting}</p>
            <p>Thank you for joining {self.app_name}! To complete your account setup and start getting personalized guidance from our expert advisors, please verify your email address.</p>
            
            <div class="code-box">
                <p style="margin: 0 0 10px 0; color: #374151; font-weight: 500;">Your verification code is:</p>
                <div class="code">{verification_code}</div>
            </div>
            
            <p>Enter this code in the verification form to activate your account. This code will expire in <strong>30 minutes</strong>.</p>
            
            <p>Once verified, you'll be able to:</p>
            <ul style="color: #374151; line-height: 1.6;">
                <li>Get personalized advice from multiple PhD advisor personas</li>
                <li>Upload and analyze your research documents</li>
                <li>Save and manage your conversation history</li>
                <li>Access specialized guidance for your research area</li>
            </ul>
            
            <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Security Notice:</strong> If you did not create an account with us, please ignore this email. Your email address will not be used for anything else.</p>
            </div>
        </div>
        <div class="footer">
            <p>Best regards,<br>{self.app_name} Team</p>
        </div>
    </div>
</body>
</html>
"""

            # Attach parts
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.from_email, to_email, text)

            logger.info(f"Email verification sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
            return False

    async def send_password_reset_email(self, to_email: str, reset_code: str) -> bool:
        """Send password reset email with verification code"""
        try:
            if not all([self.smtp_username, self.smtp_password]):
                logger.error("SMTP credentials not configured")
                return False

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Password Reset Code - {self.app_name}"
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Create HTML and text content
            text_content = f"""
Password Reset Request

Hello,

You have requested to reset your password for {self.app_name}.

Your password reset code is: {reset_code}

This code will expire in 30 minutes.

If you did not request this password reset, please ignore this email.

Best regards,
{self.app_name} Team
"""

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background-color: #f9fafb; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
        .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 40px 20px; text-align: center; }}
        .header h1 {{ color: #ffffff; margin: 0; font-size: 24px; }}
        .content {{ padding: 40px 20px; }}
        .code-box {{ background-color: #eff6ff; border: 2px solid #6366f1; border-radius: 12px; padding: 20px; text-align: center; margin: 20px 0; }}
        .code {{ font-size: 32px; font-weight: bold; color: #6366f1; letter-spacing: 4px; }}
        .warning {{ background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin: 20px 0; }}
        .footer {{ background-color: #f3f4f6; padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self.app_name}</h1>
        </div>
        <div class="content">
            <h2>Password Reset Request</h2>
            <p>Hello,</p>
            <p>You have requested to reset your password for {self.app_name}.</p>
            
            <div class="code-box">
                <p style="margin: 0 0 10px 0; color: #374151; font-weight: 500;">Your verification code is:</p>
                <div class="code">{reset_code}</div>
            </div>
            
            <p>Enter this code in the password reset form to continue. This code will expire in <strong>30 minutes</strong>.</p>
            
            <div class="warning">
                <p style="margin: 0;"><strong>Security Notice:</strong> If you did not request this password reset, please ignore this email. Your account remains secure.</p>
            </div>
        </div>
        <div class="footer">
            <p>Best regards,<br>{self.app_name} Team</p>
        </div>
    </div>
</body>
</html>
"""

            # Attach parts
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.from_email, to_email, text)

            logger.info(f"Password reset email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            return False

# Global email service instance
email_service = EmailService()