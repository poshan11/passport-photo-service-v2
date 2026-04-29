import os


def _env(name, default=None):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
db_name = os.getenv("DB_NAME", "passport_photo_db")
db_user = os.getenv("DB_USER", "appuser" if instance_connection_name else "root")
db_password = os.getenv("DB_PASSWORD", "")

if instance_connection_name:
    # Running in Cloud Run with Cloud SQL socket mounted at /cloudsql.
    DB_CONFIG = {
        "user": db_user,
        "password": db_password,
        "database": db_name,
        "unix_socket": f"/cloudsql/{instance_connection_name}",
    }
else:
    # Running locally – use public IP and port.
    DB_CONFIG = {
        "user": db_user,
        "password": db_password,
        "host": os.getenv("DB_HOST", "localhost"),
        "database": db_name,
        "port": int(os.getenv("DB_PORT", "3306")),
    }

STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "your-gcs-bucket")

STRIPE_SECRECT_KEY = _env("STRIPE_SECRECT_KEY", "")
STRIPE_WEBHOOK = _env("STRIPE_WEBHOOK", "")

zippotamus_base_url = "http://api.zippopotam.us/us/"

# walgreens configs
WALGREENS_API_KEY = _env("WALGREENS_API_KEY", "")  # Your Walgreens API key
WALGREENS_AFF_ID = _env("WALGREENS_AFF_ID", "photoapi")  # Your Affiliate ID
APP_VER = _env("APP_VER", "1.0")
DEV_INF = _env("DEV_INF", "python,3.8")  # Example device info
WALGREENS_PRODUCT_GROUP_ID = _env("WALGREENS_PRODUCT_GROUP_ID", "STDPR")
WALGREENS_PRODUCTS_URL = "https://services.walgreens.com/api/photo/products/v3"
WALGREENS_STORE_URL = "https://services.walgreens.com/api/photo/store/v3"
WALGREENS_ORDER_URL = "https://services.walgreens.com/api/photo/order/submit/v3"

WALGREENS_PRODUCTS_URL_SANDBOX = "https://services-qa.walgreens.com/api/photo/products/v3"
WALGREENS_STORE_URL_SANDBOX = "https://services-qa.walgreens.com/api/photo/store/v3"
WALGREENS_ORDER_URL_SANDBOX = "https://services-qa.walgreens.com/api/photo/order/submit/v3"


#Walmart configs
WALMART_STORE_URL = _env("WALMART_STORE_URL", "https://photos3.walmart.com/order/prints-builder")

#email address config:
ADMIN_ORDER_CONFIRMATION_EMAIL = _env("ADMIN_ORDER_CONFIRMATION_EMAIL", "orders@example.com")

#google email confirmation for adding to google photos.
CONFIRMATION_GMAIL_GOOGLE_PHOTOS = _env("CONFIRMATION_GMAIL_GOOGLE_PHOTOS", "your-gmail@example.com")

EMAIL_PASSWORD = _env("EMAIL_PASSWORD", "")
SMTP_SERVER = _env("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(_env("SMTP_PORT", "587"))

#azure creds:
AZURE_TENANT_ID = _env("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = _env("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = _env("AZURE_CLIENT_SECRET", "")

#paypal sandbox creds:
SANDBOX_PAYPAL_CLIENT_ID = _env("SANDBOX_PAYPAL_CLIENT_ID", "")
SANDBOX_PAYPAL_CLIENT_SECRET = _env("SANDBOX_PAYPAL_CLIENT_SECRET", "")
SANDBOX_PAYPAL_API_BASE = _env("SANDBOX_PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")

#paypal live creds:
LIVE_PAYPAL_CLIENT_ID = _env("LIVE_PAYPAL_CLIENT_ID", "")
LIVE_PAYPAL_CLIENT_SECRET = _env("LIVE_PAYPAL_CLIENT_SECRET", "")
LIVE_PAYPAL_API_BASE = _env("LIVE_PAYPAL_API_BASE", "https://api-m.paypal.com")

#app url:
APP_BASE_URL = _env("APP_BASE_URL", "http://0.0.0.0:5001")

# Browser Use API key
BROWSER_USE_API_KEY = _env("BROWSER_USE_API_KEY", "")

# Promo mode (temporary free offer)
PROMO_MODE_ENABLED = _env_bool("PROMO_MODE_ENABLED", False)
PROMO_DIGITAL_ONLY = _env_bool("PROMO_DIGITAL_ONLY", True)
PROMO_HIDE_FULFILLMENT_OPTIONS = _env_bool("PROMO_HIDE_FULFILLMENT_OPTIONS", True)
PROMO_BANNER_TEXT = _env("PROMO_BANNER_TEXT", "Limited-time free digital passport photo")
