from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def generate_activation_code() -> str:
    """Генерируем 6-значный код активации"""
    return str(random.randint(100000, 999999))


def send_confirmation_email(to_email: str, code: str):
    """Send a glassmorphism-style HTML email with the confirmation code (with plaintext fallback)"""
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = "Scribbles — Email Confirmation Code"

    # --- Plain text fallback (for strict clients) ---
    text_content = f"""Scribbles

We received a request to confirm your email.
Your confirmation code: {code}

Enter this code on the confirmation page to continue.
If you didn’t request this, you can ignore this email.
"""

    # --- HTML (glassmorphism) ---
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f6f6f9;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:linear-gradient(135deg,#edecee 10%,#e8d4e7 55%,#ffffff 100%);padding:28px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:440px;">
            <tr>
              <td style="
                border-radius:18px;
                padding:26px 22px;
                background:rgba(255,255,255,0.55);
                box-shadow:0 10px 40px rgba(0,0,0,0.08);
                border:1px solid rgba(255,255,255,0.35);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                ">
                <div style="text-align:center;font-family:Arial,Helvetica,sans-serif;color:#151316;">
                  <div style="font-size:22px;font-weight:700;letter-spacing:0.2px;color:#796380;margin-bottom:6px;">
                    Scribbles
                  </div>
                  <div style="font-size:14px;line-height:1.55;color:#444;margin:0 6px 16px;">
                    We received a request to confirm your email address.
                  </div>

                  <div style="
                    margin:12px auto 16px;
                    max-width:260px;
                    padding:14px 10px;
                    border-radius:12px;
                    background:rgba(255,255,255,0.65);
                    border:1px solid rgba(121,99,128,0.25);
                    box-shadow:0 6px 22px rgba(121,99,128,0.20);
                    ">
                    <div style="font-size:26px;font-weight:800;letter-spacing:3px;color:#796380;">
                      {code}
                    </div>
                  </div>

                  <div style="font-size:13px;color:#555;line-height:1.6;margin-bottom:18px;">
                    Enter this code on the confirmation page to continue.
                  </div>

                  <hr style="border:none;height:1px;background:#eaeaea;margin:16px 0 12px;">

                  <div style="font-size:12px;color:#9b9b9b;line-height:1.5;">
                    If you didn’t request this, you can safely ignore this email.
                  </div>
                </div>
              </td>
            </tr>

            <tr>
              <td style="text-align:center;font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#a1a1a7;padding:14px 6px 4px;">
                © {2025} Scribbles
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    # Attach parts (clients choose best they support)
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")
