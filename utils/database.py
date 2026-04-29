"""
Database connection pool and query utilities
"""
import mysql.connector.pooling
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Tuple
import logging
from config import DB_CONFIG

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection pool manager"""
    
    _pool = None
    
    @classmethod
    def initialize_pool(cls, pool_size: int = 10):
        """Initialize the connection pool"""
        try:
            pool_config = {
                **DB_CONFIG,
                'pool_name': 'passport_photo_pool',
                'pool_size': pool_size,
                'pool_reset_session': True,
                'autocommit': False
            }
            
            cls._pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"Database connection pool initialized with {pool_size} connections")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {str(e)}")
            raise
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """Get a database connection from the pool"""
        if cls._pool is None:
            cls.initialize_pool()
        
        connection = None
        try:
            connection = cls._pool.get_connection()
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    @classmethod
    @contextmanager
    def get_cursor(cls, dictionary: bool = True):
        """Get a cursor with automatic connection management"""
        with cls.get_connection() as connection:
            cursor = connection.cursor(dictionary=dictionary)
            try:
                yield cursor, connection
            except Exception as e:
                connection.rollback()
                raise
            else:
                connection.commit()
            finally:
                cursor.close()

class UserRepository:
    """Repository for user-related database operations"""
    
    @staticmethod
    def get_or_create_user(email: str, fname: str, lname: str, phone: str = None) -> int:
        """Get existing user or create new one"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            # Check if user exists
            select_query = "SELECT id FROM users WHERE email = %s"
            cursor.execute(select_query, (email,))
            result = cursor.fetchone()
            
            if result:
                return result['id']
            
            # Create new user
            insert_query = """
                INSERT INTO users (email, fname, lname, phone, created_at) 
                VALUES (%s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (email, fname, lname, phone))
            return cursor.lastrowid
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = "SELECT * FROM users WHERE id = %s"
            cursor.execute(query, (user_id,))
            return cursor.fetchone()

class PhotoRepository:
    """Repository for photo-related database operations"""
    
    @staticmethod
    def create_photo_record(user_id: int, processed_url: str, layout_url: str, 
                          original_url: str = None) -> int:
        """Create a new photo record"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = """
                INSERT INTO photos (user_id, original_url, processed_url, layout_url, status, created_at)
                VALUES (%s, %s, %s, %s, 'processed', NOW())
            """
            cursor.execute(query, (user_id, original_url or processed_url, processed_url, layout_url))
            return cursor.lastrowid
    
    @staticmethod
    def get_photo_by_id(photo_id: int) -> Optional[Dict]:
        """Get photo by ID"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = "SELECT * FROM photos WHERE id = %s"
            cursor.execute(query, (photo_id,))
            return cursor.fetchone()

class OrderRepository:
    """Repository for order-related database operations"""
    
    @staticmethod
    def create_order(user_id: int, photo_id: int, order_type: str, 
                    external_token: str) -> int:
        """Create a new order"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = """
                INSERT INTO orders (user_id, photo_id, order_type, order_status, 
                                  external_order_token, created_at)
                VALUES (%s, %s, %s, 'pending', %s, NOW())
            """
            cursor.execute(query, (user_id, photo_id, order_type, external_token))
            return cursor.lastrowid
    
    @staticmethod
    def update_order_status(order_id: int, status: str):
        """Update order status"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = "UPDATE orders SET order_status = %s, updated_at = NOW() WHERE id = %s"
            cursor.execute(query, (status, order_id))
    
    @staticmethod
    def get_order_by_id(order_id: int) -> Optional[Dict]:
        """Get order by ID with related data"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = """
                SELECT o.*, u.email, u.fname, u.lname, u.phone,
                       p.processed_url, p.layout_url
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN photos p ON o.photo_id = p.id
                WHERE o.id = %s
            """
            cursor.execute(query, (order_id,))
            return cursor.fetchone()

class PaymentRepository:
    """Repository for payment-related database operations"""
    
    @staticmethod
    def create_payment_record(order_id: int, gateway: str, amount: float, 
                            transaction_id: str = None) -> int:
        """Create a payment record"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = """
                INSERT INTO payments (order_id, payment_gateway, payment_status, 
                                    amount, transaction_id, created_at)
                VALUES (%s, %s, 'pending', %s, %s, NOW())
            """
            cursor.execute(query, (order_id, gateway, amount, transaction_id))
            return cursor.lastrowid
    
    @staticmethod
    def update_payment_status(order_id: int, transaction_id: str, status: str):
        """Update payment status"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = """
                UPDATE payments 
                SET transaction_id = %s, payment_status = %s, updated_at = NOW()
                WHERE order_id = %s
            """
            cursor.execute(query, (transaction_id, status, order_id))

class ReferralRepository:
    """Repository for referral-related database operations"""
    
    @staticmethod
    def create_referral_record(email: str) -> bool:
        """Create a new referral record for a customer (after first order)"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            # Only create if email exists in users table and not already in referrals
            query = """
                INSERT INTO referrals (email, referral_remaining, created_at) 
                SELECT %s, 5, NOW()
                FROM users 
                WHERE email = %s
                AND NOT EXISTS (SELECT 1 FROM referrals WHERE email = %s)
                LIMIT 1
            """
            cursor.execute(query, (email, email, email))
            return cursor.rowcount > 0
    
    @staticmethod
    def check_referral_validity(email: str) -> dict:
        """Check if email can be used as referral and return status"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            # Check if email exists in users table (completed at least one order)
            user_query = "SELECT 1 FROM users WHERE email = %s LIMIT 1"
            cursor.execute(user_query, (email,))
            user_exists = cursor.fetchone()
            
            if not user_exists:
                return {
                    "valid": False,
                    "message": "This email hasn't completed an order yet. Only existing customers can provide referrals."
                }
            
            # Check referral availability
            referral_query = "SELECT referral_remaining FROM referrals WHERE email = %s"
            cursor.execute(referral_query, (email,))
            referral = cursor.fetchone()
            
            if not referral:
                return {
                    "valid": False,
                    "message": "This customer hasn't activated their referral benefits yet."
                }
            
            if referral['referral_remaining'] <= 0:
                return {
                    "valid": False,
                    "message": "Referral limit reached. Ask another friend for referral."
                }
            
            return {
                "valid": True,
                "discount_percentage": 25,
                "referrals_remaining": referral['referral_remaining'],
                "message": "25% discount applied!"
            }
    
    @staticmethod
    def use_referral(email: str) -> bool:
        """Decrement referral count when used (atomic operation)"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = """
                UPDATE referrals 
                SET referral_remaining = referral_remaining - 1, 
                    updated_at = NOW() 
                WHERE email = %s AND referral_remaining > 0
            """
            cursor.execute(query, (email,))
            return cursor.rowcount > 0
    
    @staticmethod
    def get_referral_status(email: str) -> dict:
        """Get referral status for a customer"""
        with DatabaseManager.get_cursor() as (cursor, connection):
            query = "SELECT referral_remaining FROM referrals WHERE email = %s"
            cursor.execute(query, (email,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "has_referrals": True,
                    "referrals_remaining": result['referral_remaining']
                }
            else:
                return {
                    "has_referrals": False,
                    "referrals_remaining": 0
                }

# Initialize the database pool when module is imported
try:
    DatabaseManager.initialize_pool()
except Exception as e:
    logger.warning(f"Could not initialize database pool on import: {str(e)}")
