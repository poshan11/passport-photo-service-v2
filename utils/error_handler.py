"""
Enhanced error handling and logging utilities
"""
import logging
import traceback
import sys
from functools import wraps
from typing import Any, Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom API Exception with structured error information"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None, details: Dict = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(self.message)

    def to_dict(self):
        return {
            'error': self.message,
            'error_code': self.error_code,
            'status_code': self.status_code,
            'details': self.details,
            'timestamp': self.timestamp
        }

def handle_exceptions(func):
    """Decorator to handle exceptions consistently across API endpoints"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIError as e:
            logger.error(f"API Error in {func.__name__}: {e.message}", extra={
                'error_code': e.error_code,
                'status_code': e.status_code,
                'details': e.details
            })
            return {'error': e.message, 'status_code': e.status_code}, e.status_code
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", extra={
                'traceback': traceback.format_exc()
            })
            return {'error': 'Internal server error'}, 500
    return wrapper

def log_api_call(endpoint: str, params: Dict = None, user_id: str = None):
    """Log API call with structured information"""
    logger.info(f"API Call: {endpoint}", extra={
        'endpoint': endpoint,
        'params': params,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat()
    })

def log_processing_step(step: str, image_token: str, details: Dict = None):
    """Log image processing steps"""
    logger.info(f"Processing Step: {step}", extra={
        'step': step,
        'image_token': image_token,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat()
    })

def log_payment_event(event_type: str, order_id: str, amount: float = None, gateway: str = None):
    """Log payment-related events"""
    logger.info(f"Payment Event: {event_type}", extra={
        'event_type': event_type,
        'order_id': order_id,
        'amount': amount,
        'gateway': gateway,
        'timestamp': datetime.utcnow().isoformat()
    })

class HealthChecker:
    """System health monitoring"""
    
    @staticmethod
    def check_database_connection():
        """Check database connectivity"""
        try:
            import mysql.connector
            from config import DB_CONFIG
            
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    @staticmethod
    def check_storage_connection():
        """Check Google Cloud Storage connectivity"""
        try:
            from google.cloud import storage
            from config import STORAGE_BUCKET
            
            client = storage.Client()
            bucket = client.bucket(STORAGE_BUCKET)
            bucket.exists()
            return True
        except Exception as e:
            logger.error(f"Storage health check failed: {str(e)}")
            return False
    
    @staticmethod
    def check_external_apis():
        """Check external API connectivity"""
        checks = {}
        
        # Check Stripe
        try:
            import stripe
            from config import STRIPE_SECRET_KEY
            stripe.api_key = STRIPE_SECRET_KEY
            stripe.Account.retrieve()
            checks['stripe'] = True
        except Exception as e:
            logger.error(f"Stripe health check failed: {str(e)}")
            checks['stripe'] = False
        
        return checks
    
    @classmethod
    def get_system_health(cls):
        """Get overall system health status"""
        return {
            'database': cls.check_database_connection(),
            'storage': cls.check_storage_connection(),
            'external_apis': cls.check_external_apis(),
            'timestamp': datetime.utcnow().isoformat()
        }
