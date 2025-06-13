import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import aiosmtplib
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)
FROM_NAME = os.getenv("FROM_NAME", "GPU Yield")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Initialize Jinja2 environment for email templates
template_env = Environment(
    loader=FileSystemLoader("templates/email"),
    autoescape=True
)

class EmailService:
    def __init__(self):
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.username = SMTP_USERNAME
        self.password = SMTP_PASSWORD
        self.from_email = FROM_EMAIL
        self.from_name = FROM_NAME

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            if not self.username or not self.password:
                logger.error("SMTP credentials not configured")
                return False

            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send email using aiosmtplib for async support
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.username,
                password=self.password,
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def render_template(self, template_name: str, **kwargs) -> str:
        """
        Render email template with provided variables.
        
        Args:
            template_name: Name of the template file
            **kwargs: Template variables
            
        Returns:
            Rendered HTML content
        """
        try:
            template = template_env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return self.get_fallback_template(template_name, **kwargs)

    def get_fallback_template(self, template_name: str, **kwargs) -> str:
        """
        Get fallback HTML template when Jinja2 template fails.
        
        Args:
            template_name: Name of the template
            **kwargs: Template variables
            
        Returns:
            Fallback HTML content
        """
        base_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #3b82f6; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 8px; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">GPU Yield</div>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>© 2024 GPU Yield. All rights reserved.</p>
                    <p>If you didn't request this email, please ignore it.</p>
                </div>
            </div>
        </body>
        </html>
        """

        if template_name == "verification_email.html":
            content = f"""
                <h1>Verify Your Email Address</h1>
                <p>Hi {kwargs.get('user_name', 'there')},</p>
                <p>Thank you for signing up for GPU Yield! Please click the button below to verify your email address:</p>
                <a href="{kwargs.get('verification_url', '#')}" class="button">Verify Email</a>
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p>{kwargs.get('verification_url', '#')}</p>
                <p>This link will expire in 24 hours.</p>
            """
        elif template_name == "welcome_email.html":
            content = f"""
                <h1>Welcome to GPU Yield!</h1>
                <p>Hi {kwargs.get('user_name', 'there')},</p>
                <p>Welcome to GPU Yield! Your account has been successfully created.</p>
                <p>You can now start maximizing your GPU profits with our platform.</p>
                <a href="{FRONTEND_URL}/dashboard" class="button">Go to Dashboard</a>
                <p>If you have any questions, feel free to contact our support team.</p>
            """
        elif template_name == "password_reset.html":
            content = f"""
                <h1>Reset Your Password</h1>
                <p>Hi {kwargs.get('user_name', 'there')},</p>
                <p>You requested to reset your password. Click the button below to set a new password:</p>
                <a href="{kwargs.get('reset_url', '#')}" class="button">Reset Password</a>
                <p>If you didn't request this password reset, please ignore this email.</p>
                <p>This link will expire in 1 hour.</p>
            """
        else:
            content = f"""
                <h1>GPU Yield Notification</h1>
                <p>Hi {kwargs.get('user_name', 'there')},</p>
                <p>You have a new notification from GPU Yield.</p>
                <a href="{FRONTEND_URL}" class="button">Visit GPU Yield</a>
            """

        return base_template.format(
            title=kwargs.get('title', 'GPU Yield'),
            content=content
        )

# Create global email service instance
email_service = EmailService()

async def send_verification_email(
    to_email: str,
    user_name: str,
    verification_token: str
) -> bool:
    """
    Send email verification email.
    
    Args:
        to_email: Recipient email address
        user_name: User's name
        verification_token: Email verification token
        
    Returns:
        True if email sent successfully
    """
    verification_url = f"{BACKEND_URL}/auth/verify-email/{verification_token}"
    
    html_content = email_service.render_template(
        "verification_email.html",
        user_name=user_name,
        verification_url=verification_url,
        frontend_url=FRONTEND_URL
    )
    
    return await email_service.send_email(
        to_email=to_email,
        subject="Verify your GPU Yield account",
        html_content=html_content
    )

async def send_welcome_email(
    to_email: str,
    user_name: str
) -> bool:
    """
    Send welcome email to new user.
    
    Args:
        to_email: Recipient email address
        user_name: User's name
        
    Returns:
        True if email sent successfully
    """
    html_content = email_service.render_template(
        "welcome_email.html",
        user_name=user_name,
        frontend_url=FRONTEND_URL
    )
    
    return await email_service.send_email(
        to_email=to_email,
        subject="Welcome to GPU Yield!",
        html_content=html_content
    )

async def send_password_reset_email(
    to_email: str,
    user_name: str,
    reset_token: str
) -> bool:
    """
    Send password reset email.
    
    Args:
        to_email: Recipient email address
        user_name: User's name
        reset_token: Password reset token
        
    Returns:
        True if email sent successfully
    """
    reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    
    html_content = email_service.render_template(
        "password_reset.html",
        user_name=user_name,
        reset_url=reset_url,
        frontend_url=FRONTEND_URL
    )
    
    return await email_service.send_email(
        to_email=to_email,
        subject="Reset your GPU Yield password",
        html_content=html_content
    )

async def send_oauth_linked_email(
    to_email: str,
    user_name: str,
    provider: str
) -> bool:
    """
    Send notification email when OAuth account is linked.
    
    Args:
        to_email: Recipient email address
        user_name: User's name
        provider: OAuth provider name
        
    Returns:
        True if email sent successfully
    """
    html_content = email_service.render_template(
        "oauth_linked.html",
        user_name=user_name,
        provider=provider.title(),
        frontend_url=FRONTEND_URL
    )
    
    if not html_content or "oauth_linked.html" in html_content:
        # Use fallback template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Account Linked - GPU Yield</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1>Account Linked Successfully</h1>
                <p>Hi {user_name},</p>
                <p>Your {provider.title()} account has been successfully linked to your GPU Yield account.</p>
                <p>You can now use {provider.title()} to sign in to your account.</p>
                <p>If you didn't link this account, please contact our support team immediately.</p>
                <p>Best regards,<br>The GPU Yield Team</p>
            </div>
        </body>
        </html>
        """
    
    return await email_service.send_email(
        to_email=to_email,
        subject=f"{provider.title()} account linked to GPU Yield",
        html_content=html_content
    )

async def send_security_alert_email(
    to_email: str,
    user_name: str,
    alert_type: str,
    details: str
) -> bool:
    """
    Send security alert email.
    
    Args:
        to_email: Recipient email address
        user_name: User's name
        alert_type: Type of security alert
        details: Alert details
        
    Returns:
        True if email sent successfully
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Security Alert - GPU Yield</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #fee; border: 1px solid #fcc; border-radius: 6px; padding: 15px; margin-bottom: 20px;">
                <h1 style="color: #c33; margin: 0;">Security Alert</h1>
            </div>
            <p>Hi {user_name},</p>
            <p>We detected {alert_type} on your GPU Yield account:</p>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <strong>Details:</strong> {details}
            </div>
            <p>If this was you, no action is needed. If you didn't perform this action, please:</p>
            <ul>
                <li>Change your password immediately</li>
                <li>Review your account settings</li>
                <li>Contact our support team</li>
            </ul>
            <p>Best regards,<br>The GPU Yield Security Team</p>
        </div>
    </body>
    </html>
    """
    
    return await email_service.send_email(
        to_email=to_email,
        subject=f"Security Alert: {alert_type}",
        html_content=html_content
    )