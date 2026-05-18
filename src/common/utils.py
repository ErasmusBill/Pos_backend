import os
import random
import string
from typing import List, Optional

import PIL
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from pydantic import EmailStr
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from dotenv import load_dotenv
import blurhash
from PIL import Image

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


def send_email(background_tasks: BackgroundTasks, subject: str, recipients: List[EmailStr], body: str):
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)


def generate_image_blurhash(file_path: str) -> str:
    """Generates a blurhash string from an image file."""
    with PIL.Image.open(file_path) as img:
        img.thumbnail((32, 32))

        if img.mode != 'RGB':
            img = img.convert('RGB')

        hash_str = blurhash.encode(img, x_components=4, y_components=3)
        return hash_str


def generate_sku(name: str, category_name: str) -> str:
    """
    Generates a SKU like: CAT-NAM-RAND
    Example: ELC-LAP-42A1
    """
    # Take first 3 letters of category and name, make uppercase
    cat_prefix = category_name[:3].upper().strip()
    prod_prefix = name[:3].upper().strip()

    # Generate 4 random characters to ensure uniqueness
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

    return f"{cat_prefix}-{prod_prefix}-{random_suffix}"

SECRET_KEY = os.getenv("SECRET_KEY", "your-fallback-secret-key")

ACTIVATION_SALT = "account-activation-salt"
PASSWORD_RESET_SALT = "password-reset-salt"

def generate_token(email: str, salt: str) -> str:
    """
    Generates a signed token for a specific purpose defined by the salt.
    """
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(email, salt=salt)

def confirm_token(token: str, salt: str, expiration: int = 3600) -> Optional[str]:
    """
    Validates the token for a specific purpose (salt).
    """
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt=salt,
            max_age=expiration
        )
        return email
    except (SignatureExpired, BadSignature):
        return None

