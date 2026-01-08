"""SMTP client implementation for sending emails."""

import base64
import email.utils
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import List, Optional

from workspace_secretary.config import ServerConfig
from workspace_secretary.models import Email, EmailAddress
from workspace_secretary.oauth2 import get_access_token

logger = logging.getLogger(__name__)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


class SMTPClient:
    def __init__(self, config: ServerConfig):
        self.config = config
        self._smtp: Optional[smtplib.SMTP] = None

    def _get_xoauth2_string(self, username: str, access_token: str) -> str:
        auth_string = f"user={username}\1auth=Bearer {access_token}\1\1"
        return auth_string

    def send_message(self, message: EmailMessage) -> bool:
        if not self.config.imap.oauth2:
            raise ValueError("OAuth2 configuration required for SMTP")

        access_token, _ = get_access_token(self.config.imap.oauth2)
        username = self.config.imap.username

        try:
            smtp = smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()

            xoauth2_string = self._get_xoauth2_string(username, access_token)
            xoauth2_b64 = base64.b64encode(xoauth2_string.encode()).decode()

            code, response = smtp.docmd("AUTH", f"XOAUTH2 {xoauth2_b64}")
            if code != 235:
                logger.error(f"SMTP AUTH failed: {code} {response}")
                raise smtplib.SMTPAuthenticationError(code, response)

            smtp.send_message(message)
            smtp.quit()

            logger.info(f"Email sent successfully to {message['To']}")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise


def create_reply_mime(
    original_email: Email,
    reply_to: EmailAddress,
    body: str,
    subject: Optional[str] = None,
    cc: Optional[List[EmailAddress]] = None,
    reply_all: bool = False,
    html_body: Optional[str] = None,
) -> EmailMessage:
    """Create a MIME message for replying to an email.

    Args:
        original_email: Original email to reply to
        reply_to: Address to send the reply from
        body: Plain text body of the reply
        subject: Subject for the reply (default: prepend "Re: " to original)
        cc: List of CC recipients (default: none)
        reply_all: Whether to reply to all recipients (default: False)
        html_body: Optional HTML version of the body

    Returns:
        MIME message ready for sending
    """
    # Always use EmailMessage (modern API)
    message = EmailMessage()

    # Set the From header
    message["From"] = str(reply_to)

    # Set the To header
    to_recipients = [original_email.from_]
    if reply_all and original_email.to:
        # Add original recipients excluding the sender
        to_recipients.extend(
            [
                recipient
                for recipient in original_email.to
                if recipient.address != reply_to.address
            ]
        )

    message["To"] = ", ".join(str(recipient) for recipient in to_recipients)

    # Set the CC header if applicable
    cc_recipients = []
    if cc:
        cc_recipients.extend(cc)
    elif reply_all and original_email.cc:
        cc_recipients.extend(
            [
                recipient
                for recipient in original_email.cc
                if recipient.address != reply_to.address
            ]
        )

    if cc_recipients:
        message["Cc"] = ", ".join(str(recipient) for recipient in cc_recipients)

    # Set the subject
    if subject:
        message["Subject"] = subject
    else:
        # Add "Re: " prefix if not already present
        original_subject = original_email.subject
        if not original_subject.startswith("Re:"):
            message["Subject"] = f"Re: {original_subject}"
        else:
            message["Subject"] = original_subject

    # Set references for threading
    references = []
    if "References" in original_email.headers:
        references.append(original_email.headers["References"])
    if original_email.message_id:
        references.append(original_email.message_id)

    if references:
        message["References"] = " ".join(references)

    # Set In-Reply-To header
    if original_email.message_id:
        message["In-Reply-To"] = original_email.message_id

    # Prepare plain text content
    plain_text = body
    if original_email.content.text:
        # Quote original plain text
        quoted_original = "\n".join(
            f"> {line}" for line in original_email.content.text.split("\n")
        )
        plain_text += f"\n\nOn {email.utils.format_datetime(original_email.date or datetime.now())}, {original_email.from_} wrote:\n{quoted_original}"

    # Set main content (defaults to plain text)
    message.set_content(plain_text)

    # Add HTML alternative if provided
    if html_body:
        html_content = html_body
        if original_email.content.html:
            # Add original HTML with a divider
            html_content += (
                f'\n<div style="border-top: 1px solid #ccc; margin-top: 20px; padding-top: 10px;">'
                f"\n<p>On {email.utils.format_datetime(original_email.date or datetime.now())}, {original_email.from_} wrote:</p>"
                f'\n<blockquote style="margin: 0 0 0 .8ex; border-left: 1px solid #ccc; padding-left: 1ex;">'
                f"\n{original_email.content.html}"
                f"\n</blockquote>"
                f"\n</div>"
            )
        else:
            # Convert plain text to HTML for quoting
            original_text = original_email.content.get_best_content()
            if original_text:
                escaped_text = (
                    original_text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                escaped_text = escaped_text.replace("\n", "<br>")
                html_content += (
                    f'\n<div style="border-top: 1px solid #ccc; margin-top: 20px; padding-top: 10px;">'
                    f"\n<p>On {email.utils.format_datetime(original_email.date or datetime.now())}, {original_email.from_} wrote:</p>"
                    f'\n<blockquote style="margin: 0 0 0 .8ex; border-left: 1px solid #ccc; padding-left: 1ex;">'
                    f"\n{escaped_text}"
                    f"\n</blockquote>"
                    f"\n</div>"
                )

        message.add_alternative(html_content, subtype="html")

    # Add Date header
    message["Date"] = email.utils.formatdate(localtime=True)

    return message
