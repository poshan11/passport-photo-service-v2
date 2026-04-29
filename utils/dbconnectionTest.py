import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'user': 'appuser',
    'password': 'A1y12IS@061',
    'host': '130.211.212.25',
    'database': 'passport_photo_db',
    'port': 3306
}

def test_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            db_info = connection.get_server_info()
            print("Connected to MySQL Server version:", db_info)
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            print("You're connected to database:", record)
    except Error as e:
        print("Error while connecting to MySQL:", e)
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed.")

if __name__ == "__main__":
    test_connection()
