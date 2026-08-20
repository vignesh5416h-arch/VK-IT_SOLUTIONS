import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "vk_it_solutions.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"


    INITIAL_OWNER_EMAIL = os.getenv(
    "INITIAL_OWNER_EMAIL",
    "manojaleti222@gmail.com"
)

INITIAL_OWNER_PASSWORD = os.getenv(
    "INITIAL_OWNER_PASSWORD",
    "Manoj@18"
)
INITIAL_OWNER_NAME = os.getenv(
    "INITIAL_OWNER_NAME",
    "VK IT SOLUTIONS Owner"
)
