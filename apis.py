# apis.py
import os
import uuid
import cv2
import requests
from flask import Flask, request, jsonify
# import mysql.connector
import stripe
import base64
import config
from utils import storage_utils
import utils.process_images as process_images
import utils.generic_utils as generic_utils
from utils import order_utils
import walgreens_api
import utils.orderconfirmationemail as email_confirmation
from utils.order_utils import update_payment_record
from utils.storage_utils import extract_filename_from_url
from utils.database import DatabaseManager, ReferralRepository
from utils.browser_use_automation import run_google_photos_task

app = Flask(__name__)

DB_CONFIG = config.DB_CONFIG

# Stripe Configuration
# Set your Stripe secret key (make sure to set this in your environment variables)
stripe.api_key = config.STRIPE_SECRECT_KEY
# Webhook secret for verifying Stripe events
STRIPE_WEBHOOK_SECRET = config.STRIPE_WEBHOOK


def _promo_payload():
    return {
        "promo_mode_enabled": bool(getattr(config, "PROMO_MODE_ENABLED", False)),
        "promo_digital_only": bool(getattr(config, "PROMO_DIGITAL_ONLY", True)),
        "promo_hide_fulfillment_options": bool(getattr(config, "PROMO_HIDE_FULFILLMENT_OPTIONS", True)),
        "promo_banner_text": getattr(config, "PROMO_BANNER_TEXT", "") or "",
    }


def _promo_free_order(order_data):
    payment_info = (order_data or {}).get("payment_info") or {}
    amount_raw = payment_info.get("amount", "0")
    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0.0
    return amount <= 0.0 or payment_info.get("gateway") == "free"

##############################
# Endpoints
##############################

@app.route('/')
def index():
    return "Welcome to the backend"

@app.route('/process', methods=['POST'])
def process_endpoint():
    """
    Process an uploaded image and return a token identifier.
    The processed image is saved to a temporary location (/tmp).
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file found, Please provide a photo file'}), 400

    try:
        image = generic_utils.load_image(file, file.filename)
    except Exception as e:
        return jsonify({'error': 'Please re-upload a valid photo format: .jpeg/.jpg/.heic' + str(e)}), 400

    # Extract document type from form data
    doc_type = request.form.get('docType', 'default')
    
    # Extract document configuration if provided (as JSON string)
    doc_config_str = request.form.get('docConfig')
    doc_config = None
    if doc_config_str:
        try:
            import json
            doc_config = json.loads(doc_config_str)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid document configuration JSON'}), 400
    
    try:
        processed_img = process_images.process_image_array(image, doc_config, doc_type)
    except Exception as e:
        return jsonify({'error': 'Error: ' + str(e)}), 400

    success, encoded_img = cv2.imencode('.jpg', processed_img)
    if not success:
        return jsonify({'error': 'Image encoding failed.'}), 500

    # Generate a unique token and save the processed image to /tmp
    token = str(uuid.uuid4())
    temp_filename = f"/tmp/processed_{token}.jpg"
    with open(temp_filename, 'wb') as f:
        f.write(encoded_img.tobytes())
    
    # Store document type information with the token for later use
    doc_type_filename = f"/tmp/doc_type_{token}.txt"
    with open(doc_type_filename, 'w') as f:
        f.write(doc_type)

    return jsonify({'token': token}), 200


@app.route('/preview/<token>', methods=['GET'])
def preview(token):
    """
    Return a watermarked preview of the processed image.
    """
    temp_filename = f"/tmp/processed_{token}.jpg"
    if not os.path.exists(temp_filename):
        return jsonify({'error': 'Processed image not found.'}), 404
    try:
        return process_images.add_watermark(temp_filename)
    except Exception as e:
        return jsonify({"error": "Error generating preview: " + str(e)}), 500

# ToDO: save original Photo as well.

@app.route('/findWalgreensStore')
def find_nearest_pickup_stores():
    """
    Converts the zip code to latitude/longitude and uses the Walgreens API to
    determine the nearest store and its details.
    Returns a dictionary of pickup details.
    """
    zip_code = request.args.get("zip_code")
    lat, lng = order_utils.convert_zip_to_geocode(zip_code)
    product_id = walgreens_api.get_4x6_product_id()  # Assumes this method exists.
    stores = walgreens_api.search_walgreens_stores(lat, lng, product_id)
    if not stores:
        raise Exception("No nearby store found for pickup.")
    return stores

@app.route('/getCost', methods=['GET'])
def get_cost():
    try:
        with DatabaseManager.get_cursor() as (cursor, connection):
            # Assuming there's only one row with the immutable cost config.
            query = """
                SELECT 
                    digital_cost_regular, 
                    digital_cost_promotional, 
                    pickup_cost_regular, 
                    pickup_cost_promotional, 
                    shipping_cost_regular, 
                    shipping_cost_promotional
                FROM cost_config 
                LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Cost configuration not found.'}), 404
            promo = _promo_payload()
            if promo["promo_mode_enabled"]:
                # Temporary promo mode: zero-out advertised prices.
                result["digital_cost_promotional"] = "0.00"
                if not promo["promo_digital_only"]:
                    result["pickup_cost_promotional"] = "0.00"
                    result["shipping_cost_promotional"] = "0.00"
            result.update(promo)
            return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'DB error: ' + str(e)}), 500


@app.route('/change-background', methods=['POST'])
def change_background():
    """
    Change the background color of a processed image.
    
    Expected JSON payload:
    {
        "token": "processed_image_token",
        "background_color": "light_blue"  // or "white", "blue", "red", "gray", etc.
    }
    
    Returns the new image with changed background as a response.
    """
    try:
        print("[DEBUG] Background change request received")
        data = request.get_json()
        if not data:
            print("[ERROR] No JSON data provided")
            return jsonify({'error': 'No JSON data provided.'}), 400
            
        token = data.get('token')
        background_color = data.get('background_color', 'white')
        
        print(f"[DEBUG] Token: {token}, Background color: {background_color}")
        
        if not token:
            print("[ERROR] Token is required")
            return jsonify({'error': 'Token is required.'}), 400
            
        # Check if the processed image exists
        temp_filename = f"/tmp/processed_{token}.jpg"
        print(f"[DEBUG] Looking for file: {temp_filename}")
        
        if not os.path.exists(temp_filename):
            print(f"[ERROR] Processed image not found: {temp_filename}")
            return jsonify({'error': f'Processed image not found for token: {token}'}), 404
            
        print(f"[DEBUG] File exists, changing background to: {background_color}")
        
        # Load the image and change background
        changed_img = process_images.change_background_color(temp_filename, background_color)
        
        # Save the new image with a new token
        new_token = str(uuid.uuid4())
        new_temp_filename = f"/tmp/processed_{new_token}.jpg"
        
        print(f"[DEBUG] Saving new image with token: {new_token}")
        
        success, encoded_img = cv2.imencode('.jpg', changed_img)
        if not success:
            print("[ERROR] Image encoding failed")
            return jsonify({'error': 'Image encoding failed.'}), 500
            
        with open(new_temp_filename, 'wb') as f:
            f.write(encoded_img.tobytes())
        
        # Copy document type file for the new token
        doc_type_filename = f"/tmp/doc_type_{token}.txt"
        new_doc_type_filename = f"/tmp/doc_type_{new_token}.txt"
        if os.path.exists(doc_type_filename):
            import shutil
            shutil.copy2(doc_type_filename, new_doc_type_filename)
            print(f"[DEBUG] Copied document type file for new token")
        
        print(f"[DEBUG] Background change successful, new token: {new_token}")
        
        return jsonify({
            'success': True,
            'new_token': new_token,
            'message': f'Background changed to {background_color}'
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Background change failed: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Background change failed: {str(e)}'}), 500


@app.route('/createOrder', methods=['POST'])
def create_order():
    """
    For shipping orders, a placeholder order message is returned since no tracking exists.
    """
    try:
        # Step 1: Validate and extract data.
        data = request.get_json()
        order_data = order_utils.validate_order_data(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

        # Step 2: Upload images (processed and composite).
    try:
        processed_storage_url, composite_storage_url, proc_path, comp_path =  storage_utils.upload_images(
            order_data.get('token'), order_data.get('selected_layout')
        )
    except Exception as e:
        return jsonify({'error': 'Image upload error: ' + str(e)}), 500

        # Step 3: Update Users and Photo tables.
    try:
        user_id = order_utils.add_user_in_db(order_data['email'], order_data['fname'], order_data['lname'],
                                             order_data['phone'])
    except Exception as e:
        return jsonify({'error': 'Users DB error: ' + str(e)}), 500

    try:
        photo_id = order_utils.add_photos_in_db(user_id, processed_storage_url, composite_storage_url)
    except Exception as e:
        return jsonify({'error': 'Photo DB error: ' + str(e)}), 500

    # Step 4: Update Orders DB (the create_order_in_db method should accept pickup_details).
    try:
        order_id, external_token = order_utils.create_order_in_db(user_id, photo_id, order_data['order_type'])
    except Exception as e:
        return jsonify({'error': 'Order DB error: ' + str(e)}), 500

    # Step 5: Update Payments DB
    try:
        order_utils.add_new_pending_payment(order_id, order_data["payment_info"])
    except Exception as e:
        return jsonify({'error': 'Payment DB error: ' + str(e)}), 500

    # Step 6: Do needful according to the order type. No extra steps needed for digital download.
    # if order_data['order_type'] == 'download':
    try:
        if order_data['order_type'] == 'shipping':
            shipping_address = order_data.get('shipping_address')
            order_utils.add_new_shipping(order_id, shipping_address)
            # do something

        # elif order_data['order_type'] == 'pickup':
            # we will call pickip automation API after successful payment capture.
            # order_utils.process_pickup_order(order_id,  order_data, composite_storage_url)

    except Exception as e:
        return jsonify({'error': 'Shipping or pickup DB error: ' + str(e)}), 500

    # Step 7: Cleanup local files.
    try:
        os.remove(proc_path)
        os.remove(comp_path)
    except Exception:
        pass

    # Step 8: Capture the Payment
    if _promo_free_order(order_data):
        try:
            update_payment_record(order_id, "FREE_PROMO", "succeeded")
        except Exception as e:
            return jsonify({'error': 'Free promo payment record update error: ' + str(e)}), 500
    elif order_data["payment_info"]["gateway"] == "paypal":
        try:
            capture_result = capture_paypal_order(order_data)
            # update payments DB of the successful capture_payment
            try:
                purchase_unit = capture_result["purchase_units"][0]
                capture_info = purchase_unit["payments"]["captures"][0]
                transaction_id = capture_info["id"]
                payment_status = capture_info["status"]
            except (KeyError, IndexError):
                transaction_id = "N/A"
                payment_status = "unknown"
            update_payment_record(order_id, transaction_id, payment_status)
        except Exception as e:
            return jsonify({'error': 'PayPal capture error: ' + str(e)}), 500

    elif order_data["payment_info"]["gateway"] == "stripe":
        # For Stripe, capture the PaymentIntent.
        payment_intent_id = order_data["payment_info"].get("payment_intent_id")
        if not payment_intent_id:
            return jsonify({"error": "Missing payment_intent_id in order data."}), 400
        try:
            captured_intent = stripe.PaymentIntent.capture(payment_intent_id)
            print(captured_intent)
            try:
                transaction_id = captured_intent["latest_charge"]
            except (KeyError, IndexError):
                transaction_id = "N/A"
            payment_status = captured_intent.get("status", "unknown")

            # update payments DB of the successful capture_payment
            update_payment_record(order_id, transaction_id, payment_status)
        except Exception as e:
            return jsonify({'error': 'Payment capture error: ' + str(e)}), 500

    # Step 8.5: Process referral usage after successful payment
    try:
        referral_info = order_data.get('referral_info')
        if referral_info and referral_info.get('referral_email'):
            referral_email = referral_info.get('referral_email')
            print(f"[DEBUG] Processing referral usage for {referral_email}")
            
            # Decrement referral count now that payment is successful
            success = ReferralRepository.use_referral(referral_email)
            if success:
                print(f"[DEBUG] Referral count decremented for {referral_email}")
            else:
                print(f"[WARNING] Failed to decrement referral count for {referral_email}")
    except Exception as e:
        print(f"[WARNING] Failed to process referral usage: {str(e)}")
        # Don't fail the order if referral processing fails

    # step 9: Send email notification to customer and admin
    try:
        digital_photo_name = extract_filename_from_url(processed_storage_url)
        template_photo_name = extract_filename_from_url(composite_storage_url)
        
        digital_image_bytes, digital_content_type = storage_utils.download_file_from_storage(digital_photo_name)
        template_image_bytes, template_content_type = storage_utils.download_file_from_storage(template_photo_name)
        
        email_confirmation.send_confirmation_email(order_data.get('email'), external_token, digital_photo_name, digital_image_bytes, digital_content_type, template_photo_name, template_image_bytes, template_content_type, order_data.get('order_type'))
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")
    try:
        email_confirmation.send_admin_notification("New Order", order_data, digital_photo_name, digital_image_bytes, digital_content_type, template_photo_name, template_image_bytes, template_content_type)
    except Exception as e:
        print(f"Error sending admin notification: {str(e)}")

    # Note: Google Photos automation is now handled by a separate API endpoint
    # Call /run_pickup_automation with the order data after this API returns


    # Step 10: Add customer to referral system after successful order
    try:
        customer_email = order_data.get('email')
        if customer_email:
            referral_created = ReferralRepository.create_referral_record(customer_email)
            if referral_created:
                print(f"[DEBUG] Referral record created for {customer_email}")
            else:
                print(f"[DEBUG] Referral record already exists for {customer_email}")
    except Exception as e:
        print(f"[WARNING] Failed to create referral record: {str(e)}")
        # Don't fail the order if referral creation fails

    # Build final response after successful capture
    response = {
        'external_order_token': external_token,
        'order_token': order_data['token'],  # Direct access since this is guaranteed to exist after validation
        'order_id': order_id,
        'composite_image_url': composite_storage_url,
        'processed_image_url': processed_storage_url,
        'payment_status': 'captured'
    }

    if order_data['order_type'] == 'shipping':
        response['shipping_message'] = "Your order will be shipped via USPS First-Class Mail. You should receive it within 2-5 business days."
        
    return jsonify(response), 200


##############################
# Pickup Automation Endpoint

@app.route('/run_pickup_automation', methods=['POST'])
def run_pickup_automation():
    """
    Separate API endpoint for initiating Google Photos pickup automation.
    This should be called after the main order is created successfully.
    
    Expected request format:
    {
        "token": "order_token",
        "fname": "customer_first_name",
        "lname": "customer_last_name",
        "email": "customer_email",
        "phone": "customer_phone",
        "pickup_lookup_address": "94707",
        "processed_storage_url": "processed_image.jpg",
        "composite_storage_url": "composite_image.jpg"
    }
    """
    try:
        # Step 1: Validate and extract data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided.'}), 400
            
        # Required fields for the automation
        required_fields = ['order_token', 'fname', 'lname', 'email', 'pickup_lookup_address', 
                          'processed_storage_url', 'composite_storage_url']
        
        # Check for missing fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {missing_fields}'}), 400
            
        # Prepare the order data for the browser automation
        photo_order_data = {
            'order_token': data.get('order_token'),
            'order_type': 'pickup',
            'fname': data.get('fname'),
            'lname': data.get('lname'),
            'email': data.get('email'),
            'phone': data.get('phone', ''),
            'pickup_lookup_address': data.get('pickup_lookup_address'),
            'template_photo_name': extract_filename_from_url(data.get('composite_storage_url')),
            'digital_photo_name': extract_filename_from_url(data.get('processed_storage_url'))
        }
        
        # Run the Google Photos automation with the order data
        task_id = run_google_photos_task(photo_order_data)
        
        if task_id:
            return jsonify({
                'success': True,
                'message': 'Google Photos pickup automation started successfully',
                'task_id': task_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start Google Photos automation'
            }), 500
            
    except Exception as e:
        print(f"Error in pickup automation: {str(e)}")
        return jsonify({
            'error': f'Failed to run pickup automation: {str(e)}'
        }), 500


##############################
# Payment Endpoints (Stripe)
##############################

@app.route("/create-payment-intent", methods=["POST"])
def create_payment_intent():
    """
    Create a Payment Intent on Stripe.
    Expects a JSON payload with:
      - amount: Payment amount in cents (e.g., 1000 for $10)
      - metadata (optional): For example, {"order_id": "123"}
    Returns the client secret for the Payment Intent.
    """
    data = request.get_json()
    try:
        amount = int(data["amount"])
    except (KeyError, ValueError):
        return jsonify({"error": "Invalid or missing amount"}), 400

    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="usd",
            capture_method="manual",
            metadata=data.get("metadata", {})
        )
        return jsonify({
            "clientSecret": payment_intent.client_secret,
            "payment_intent_id": payment_intent.id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Example endpoint to capture a PaymentIntent in apis.py
@app.route("/capture-payment", methods=["POST"])
def capture_payment():
    data = request.get_json()
    payment_intent_id = data.get("payment_intent_id")
    if not payment_intent_id:
        return jsonify({"error": "Missing payment_intent_id"}), 400

    try:
        captured_intent = stripe.PaymentIntent.capture(payment_intent_id)
        return jsonify({"status": "Payment captured", "payment_intent": captured_intent})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    """
    Listen for Stripe webhook events.
    Verifies the signature and processes events (e.g., payment_intent.succeeded) to update order status.
    """
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        order_id = payment_intent.get("metadata", {}).get("order_id")
        if order_id:
            try:
                with DatabaseManager.get_cursor() as (cursor, connection):
                    update_query = "UPDATE orders SET payment_status = 'completed' WHERE id = %s"
                    cursor.execute(update_query, (order_id,))
            except Exception as e:
                print(f"Error updating order {order_id}: {e}")

    return "Success", 200

# PayPal configuration – ensure these environment variables are set in your environment.
PAYPAL_CLIENT_ID = config.LIVE_PAYPAL_CLIENT_ID
PAYPAL_CLIENT_SECRET = config.LIVE_PAYPAL_CLIENT_SECRET
PAYPAL_API_BASE = config.LIVE_PAYPAL_API_BASE


def get_paypal_access_token():
    """
    Obtain an access token from PayPal using client credentials.
    """
    auth_string = f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    url = f"{PAYPAL_API_BASE}/v1/oauth2/token"
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get PayPal access token: {response.text}")


@app.route("/create-paypal-order", methods=["POST"])
def create_paypal_order():
    """
    Create a PayPal order and return the order ID along with an approval link.
    Expects a JSON payload with:
      - amount: A string value (e.g., "10.00")
      - currency: (optional) Defaults to "USD"
    """
    try:
        data = request.get_json()
        print(f"[PayPal] Received request data: {data}")  # Debug logging
        
        amount = data.get("amount")
        if not amount:
            print(f"[PayPal] Error: Amount is missing")
            return jsonify({"error": "Amount is required"}), 400
            
        # Validate and format amount
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                print(f"[PayPal] Error: Invalid amount {amount}")
                return jsonify({"error": "Amount must be greater than 0"}), 400
            # Format to 2 decimal places as required by PayPal
            formatted_amount = f"{amount_float:.2f}"
            print(f"[PayPal] Formatted amount: {formatted_amount}")
        except (ValueError, TypeError) as e:
            print(f"[PayPal] Error parsing amount {amount}: {str(e)}")
            return jsonify({"error": "Invalid amount format"}), 400
            
        currency = data.get("currency", "USD")

        access_token = get_paypal_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        order_payload = {
            "intent": "AUTHORIZE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": formatted_amount
                    }
                }
            ],
            "application_context": {
                "brand_name": "Passport Photo app",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
                "return_url": "passportphotoapp://paypal-success",  # only for approvals
                "cancel_url": "passportphotoapp://paypal-cancel"    # only for cancellations
            }
        }
        url = f"{PAYPAL_API_BASE}/v2/checkout/orders"
        response = requests.post(url, headers=headers, json=order_payload)
        if response.status_code in [200, 201]:
            order = response.json()
            # Extract the approval URL from the response links
            approval_url = next((link["href"] for link in order.get("links", []) if link["rel"] == "approve"), None)

            print("APPROVED URL: ", approval_url)
            print("Order: ", order)
            return jsonify({"orderID": order["id"], "approval_url": approval_url})
        else:
            return jsonify({"error": "Failed to create PayPal order", "details": response.text}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def capture_paypal_order(order_data):
    paypal_order_id = order_data["payment_info"].get("paypal_order_id")
    if not paypal_order_id:
        raise Exception("Missing PayPal order ID in order data.")
    access_token = get_paypal_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    url = f"{PAYPAL_API_BASE}/v2/checkout/orders/{paypal_order_id}/capture"
    response = requests.post(url, headers=headers)
    if response.status_code not in [200, 201]:
        raise Exception(f"Failed to capture PayPal order: {response.text}")
    capture_result = response.json()

    # Extract the capture transaction ID from the response.
    try:
        transaction_id = capture_result["purchase_units"][0]["payments"]["captures"][0]["id"]
    except (KeyError, IndexError):
        transaction_id = "N/A"

    # Optionally, store it in the capture_result for later use.
    capture_result["transaction_id"] = transaction_id
    return capture_result


@app.route("/paypal-return", methods=["GET"])
def paypal_return():
    """
    Endpoint set as return_url.
    It expects a query parameter (e.g., ?token=ORDER_ID) and then captures the order.
    """
    order_id = request.args.get("token")
    if not order_id:
        return "Missing order token", 400
    try:
        access_token = get_paypal_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        url = f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture"
        response = requests.post(url, headers=headers)
        if response.status_code in [200, 201]:
            capture_result = response.json()
            # Optionally update your order record in the database here.
            return jsonify({"status": "success", "capture_result": capture_result})
        else:
            return f"Failed to capture order: {response.text}", 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

##############################
# Referral System Endpoints
##############################

@app.route('/check-referral', methods=['POST'])
def check_referral():
    """
    Check if an email can be used as a referral code (validation only).
    Does NOT decrement the referral count - that happens after successful payment.
    
    Expected JSON payload:
    {
        "referral_email": "friend@gmail.com"
    }
    
    Returns referral validity and discount information.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided.'}), 400
        
        referral_email = data.get('referral_email', '').strip().lower()
        if not referral_email:
            return jsonify({'error': 'Referral email is required.'}), 400
        
        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, referral_email):
            return jsonify({
                'valid': False,
                'message': 'Please enter a valid email address.'
            }), 400
        
        # Check referral validity (but don't decrement count yet)
        referral_status = ReferralRepository.check_referral_validity(referral_email)
        
        # Return the validation result without decrementing the count
        # The count will be decremented only after successful payment
        return jsonify(referral_status), 200
        
    except Exception as e:
        print(f"Error in check_referral: {str(e)}")
        return jsonify({
            'error': 'Failed to process referral. Please try again.'
        }), 500

@app.route('/referral-status/<email>', methods=['GET'])
def get_referral_status(email):
    """
    Get referral status for a customer (for informational purposes).
    
    Returns the current referral count for the specified email.
    """
    try:
        if not email:
            return jsonify({'error': 'Email is required.'}), 400
        
        email = email.strip().lower()
        status = ReferralRepository.get_referral_status(email)
        
        return jsonify(status), 200
        
    except Exception as e:
        print(f"Error in get_referral_status: {str(e)}")
        return jsonify({
            'error': 'Failed to get referral status.'
        }), 500

@app.route("/paypal-cancel", methods=["GET"])
def paypal_cancel():
    """
    Endpoint set as cancel_url.
    Simply notifies that the payment was cancelled.
    """
    return jsonify({"status": "cancelled", "message": "Payment was cancelled by the user."})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
