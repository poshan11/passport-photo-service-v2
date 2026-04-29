import requests
from config import DB_CONFIG
# import mysql.connector
import uuid
from config import zippotamus_base_url
from utils.database import UserRepository, PhotoRepository, OrderRepository, PaymentRepository, DatabaseManager
import walgreens_api


def validate_order_data(data):
    # Required common fields.
    required_fields = ['email', 'fname', 'lname', 'processed_image_token', 'order_type', 'selected_layout',
                       'payment_info']
    missing_fields = [f for f in required_fields if f not in data]
    if missing_fields:
        raise Exception("Missing required fields: " + ", ".join(missing_fields))

    validated = {
        "email": data['email'],
        "fname": data['fname'],
        "lname": data['lname'],
        "token": data['processed_image_token'],
        "order_type": data['order_type'],
        "shipping_address": data.get('shipping_address') if data['order_type'] == 'shipping' else 'N/A',
        "zip_code": data.get('zip_code', 'N/A'),
        "selected_layout": data['selected_layout'],
        "payment_info": data['payment_info'],
        "phone": data.get('phone', 'N/A')
    }

    # If order type is pickup, ensure required pickup details are provided.
    if data['order_type'] == 'pickup':
        pickup_lookup_address = data.get('pickupAddress', {})
        # pickup_required = ['storeNum', 'storeName', 'street', 'city', 'state', 'zip_code', 'promiseTime', 'distance']
        # missing_pickup = [field for field in pickup_required if not pickup.get(field)]
        if not data.get('pickupAddress'):
            raise Exception("Missing pickup lookup address.")

        # Build the nested pickup_details dictionary.
        validated['pickup_lookup_address'] = pickup_lookup_address
    print("Validated: ", validated)
    return validated


def convert_zip_to_geocode(zip_code):
    url = zippotamus_base_url + zip_code
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        places = data.get("places")
        if places and len(places) > 0:
            latitude = places[0].get("latitude")
            longitude = places[0].get("longitude")
            try:
                return float(latitude), float(longitude)
            except ValueError:
                raise Exception("Invalid latitude/longitude values received.")
        else:
            raise Exception("No location data found for the provided zip code.")
    else:
        raise Exception(f"Geocoding failed: Received status code {response.status_code}")

def add_user_in_db(email, fname, lname, phone):
    try:
        user_id = UserRepository.get_or_create_user(email, fname, lname, phone)
    except Exception as e:
        raise Exception('User DB error: ' + str(e))
    return user_id

def add_photos_in_db(user_id, processed_storage_url, composite_storage_url):
    try:
        photo_id = PhotoRepository.create_photo_record(user_id, processed_storage_url, composite_storage_url)
    except Exception as e:
        raise Exception('Photo DB error: ' + str(e))
    return photo_id


def add_new_shipping(order_id, shipping_address):
    try:
        # Use cursor from the DatabaseManager
        with DatabaseManager.get_cursor() as (cursor, connection):
            shipping_query = """
                INSERT INTO shipping_info (order_id, shipping_address, carrier, tracking_number, shipping_label_url, shipping_status, shipping_cost)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(shipping_query, (
                order_id,
                shipping_address,
                'USPS First-Class Mail',
                "N/A",  # No tracking number for now
                None,  # No shipping label URL generated
                'not_shipped_yet',
                0.73
            ))
            shipping_id = cursor.lastrowid
    except Exception as e:
        raise Exception(e)
    return shipping_id

def create_order_in_db(user_id, photo_id, order_type):
    """
    Insert records into orders.
    Generate and return an external order token.
    """
    try:
        external_token = str(uuid.uuid4())
        order_id = OrderRepository.create_order(user_id, photo_id, order_type, external_token)
    except Exception as e:
        raise Exception(e)
    return order_id, external_token

def add_new_pending_payment(order_id, payment_info):
    try:
        payment_id = PaymentRepository.create_payment_record(order_id, payment_info.get('gateway'), payment_info.get('amount'), payment_info.get('transaction_id'))
    except Exception as e:
        raise Exception(e)
    return payment_id

def update_payment_record(order_id, transaction_id, payment_status):
    try:
        PaymentRepository.update_payment_status(order_id, transaction_id, payment_status)
    except Exception as e:
        raise Exception("Failed to update payment record: " + str(e))

def add_new_pickup_order(order_id, pickup_details):
    try:
        with DatabaseManager.get_cursor() as (cursor, connection):
            pickup_query = """
                INSERT INTO pickups (order_id, store_num, store_name, street, city, state, zip, promise_time, store_type, distance, vendor_order_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(pickup_query, (
                order_id,
                pickup_details.get("store_num"),
                pickup_details.get("store_name"),
                pickup_details.get("street"),
                pickup_details.get("city"),
                pickup_details.get("state"),
                pickup_details.get("zip"),
                pickup_details.get("promise_time"),
                pickup_details.get("store_type", "walgreens"),
                pickup_details.get("distance"),
                pickup_details.get("vendor_order_id")
            ))
            pickup_id = cursor.lastrowid
    except Exception as e:
        raise Exception('Pickup DB error: ' + str(e))
    return pickup_id


def process_pickup_order(order_id, order_data, composite_storage_url):
    """
    Submits a Walgreens order and creates a new entry in the pickups table.
    """
    try:
        # Use the nested pickup_details dictionary.
        pickup_info = order_data['pickup_details']
        # Generate product details if not present
        if not pickup_info.get('product_details'):
            product_id = walgreens_api.get_4x6_product_id()
            product_details = [{
                "productId": product_id,
                "imageDetails": [{
                    "qty": "1",
                    "url": composite_storage_url
                }]
            }]
            pickup_info['product_details'] = product_details

        # print("Pickup Info: ", pickup_info)
        walgreens_order = walgreens_api.submit_walgreens_order(
            order_data['fname'],
            order_data['lname'],
            order_data['phone'],
            order_data['email'],
            pickup_info['store_num'],
            pickup_info['promise_time'],
            pickup_info['product_details']
        )
        # print("Walgreens order: ", walgreens_order)

        # Check the status field; raise an exception if not successful.
        if walgreens_order.get("status") != "success":
            raise Exception("Failed to place order at Walgreens: " + str(walgreens_order.get("errDesc")))
    except Exception as e:
        raise Exception(e)

    try:
        # Build pickup details for DB insertion using pickup_info
        pickup_details = {
            "store_num": pickup_info.get("store_num"),
            "store_name": pickup_info.get("store_name", "Walgreens"),
            "street": pickup_info.get("street", ""),
            "city": pickup_info.get("city", ""),
            "state": pickup_info.get("state", ""),
            "zip": pickup_info.get("zip"),
            "promise_time": pickup_info.get("promise_time"),
            "store_type": pickup_info.get("store_type", "walgreens"),
            "distance": pickup_info.get("distance"),
            "vendor_order_id": walgreens_order.get("vendorOrderId")
        }
        # print("pickup_details: ", pickup_details)
        pickup_id = add_new_pickup_order(order_id, pickup_details)
    except Exception as e:
        raise Exception (e)

    return pickup_id


