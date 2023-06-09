import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# The root of all baked data
DATA_DIR = BASE_DIR / "data"

# --------------------------------------------------------------------
# Security settings
# --------------------------------------------------------------------

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = os.environ.get("DEBUG", "NO") == "YES"
VERBOSE = os.environ.get("VERBOSE", "NO") == "YES"

ALLOWED_HOSTS = [
    host for host in os.environ.get("ALLOWED_HOSTS", "").split(",") if host
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# --------------------------------------------------------------------
# Application config
# --------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_distill",
    "server.legistar",
    "server.documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "server.wsgi.application"


# --------------------------------------------------------------------
# Database config
# --------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DATA_DIR / "db.sqlite3"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --------------------------------------------------------------------
# I18N & L10N config
# --------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------
# OpenAI config
# --------------------------------------------------------------------

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_ORGANIZATION = os.environ.get("OPENAI_ORGANIZATION")


# --------------------------------------------------------------------
# Static & Media files
# --------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = "/tmp/engage-static/"

# We bake data directly into the image, so we don't need to collect
MEDIA_ROOT = str(DATA_DIR / "media")
MEDIA_URL = "media/"


# --------------------------------------------------------------------
# Static site generation
# --------------------------------------------------------------------

# We use django-distill to generate a static site
# https://django-distill.readthedocs.io/en/latest/
DISTILL_DIR = str(BASE_DIR / "dist")
