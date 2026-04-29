# import config
import msal
import requests
import sys
import os
import base64
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config
from utils.storage_utils import download_file_from_storage, extract_filename_from_url

TENANT_ID = config.AZURE_TENANT_ID
CLIENT_ID = config.AZURE_CLIENT_ID
CLIENT_SECRET = config.AZURE_CLIENT_SECRET
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_access_token():
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception("Could not obtain access token: " + str(result.get("error_description")))


def send_confirmation_email(to_email, order_token, digital_photo_name=None, digital_image_bytes=None, digital_content_type=None, template_photo_name=None, template_image_bytes=None, template_content_type=None, order_type=None):
    """
    Send order confirmation email with optional photo attachment.
    
    Args:
        to_email: Recipient email address
        order_token: Order reference number
        digital_image_bytes: Digital image bytes
        digital_content_type: Digital image content type
        template_image_bytes: Template image bytes
        template_content_type: Template image content type
        order_type: Type of order (shipping, pickup, or digital)
    """
    access_token = get_access_token()
    endpoint = f"https://graph.microsoft.com/v1.0/users/{config.ADMIN_ORDER_CONFIRMATION_EMAIL}/sendMail"

    # Prepare order-specific messaging
    if order_type == 'shipping':
        order_specific_message = "<p><strong>Shipping Information:</strong> Your order will be shipped via USPS First-Class Mail. You should receive it within 2-5 business days.</p>"
    elif order_type == 'pickup':
        order_specific_message = "<p><strong>Pickup Information:</strong> We will shortly email you with details for the store pickup. Your order should be ready for pickup within an hour!</p>"
    else:
        order_specific_message = "<p>Your photos are attached to this email. You can easily self print them at your local stores like Walmart, Walgreens or CVS Photos.</p>"

    # Prepare base email message
    email_message = {
        "message": {
            "subject": "Order Confirmation - Passport Photo, ID Photo",
            "body": {
                "contentType": "HTML",
                "content": f"""
                    <html>
                      <body>
                        <p>Hi,</p>
                        <p>Your order has been placed successfully!</p>
                        <p><strong>Order Reference:</strong> {order_token}</p>
                        <p>Thank you for choosing our Passport Photo Service!</p>
                        {order_specific_message}
                        <div style="background-color: #f8f9fa; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0; border-radius: 4px;">
                            <h3 style="color: #28a745; margin: 0 0 10px 0; font-size: 16px;"> Get 25% Off Your Next Order!</h3>
                            <p style="margin: 0; color: #495057; font-size: 14px;">Share your email with friends and family to give them 25% off their first order!</p>
                        </div>
                        <p>For feedback, reviews, or suggestions, please contact us at {config.ADMIN_ORDER_CONFIRMATION_EMAIL}</p>
                        <p>Cheers!<br>Passport Photo, ID Photo Team</p>
                      </body>
                    </html>
                """
            },
            "from": {
                "emailAddress": {
                    "address": config.ADMIN_ORDER_CONFIRMATION_EMAIL
                }
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": to_email
                    }
                }
            ]
        },
        "saveToSentItems": "true"
    }
    
    # Initialize attachments list
    attachments = []
    
    # Add GCS attachment if image_path is provided
    if digital_photo_name:
        # Add to attachments list
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": digital_photo_name,
            "contentType": digital_content_type,
            "contentBytes": base64.b64encode(digital_image_bytes).decode('utf-8')
        })
    
    if template_photo_name:
        # Add to attachments list
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": template_photo_name,
            "contentType": template_content_type,
            "contentBytes": base64.b64encode(template_image_bytes).decode('utf-8')
        })
    
    # Add attachments to email if any were successfully prepared
    if attachments:
        email_message["message"]["attachments"] = attachments

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.post(endpoint, headers=headers, json=email_message)
    if response.status_code == 202:
        print("Confirmation email sent successfully.")
    else:
        print(f"Error: Failed to send confirmation email: {response.status_code} {response.text}")


def send_admin_notification(order_type, order_data, digital_photo_name=None, digital_image_bytes=None, digital_content_type=None, template_photo_name=None, template_image_bytes=None, template_content_type=None):
    access_token = get_access_token()
    endpoint = f"https://graph.microsoft.com/v1.0/users/{config.ADMIN_ORDER_CONFIRMATION_EMAIL}/sendMail"

    # Construct the email message payload.
    email_message = {
        "message": {
            "subject": f"{order_type} Received",
            "body": {
                "contentType": "HTML",
                "content": f"""
                <html>
                  <body>
                    <p><strong>Order Type:</strong> {order_data.get('order_type')}</p>
                    <p><strong>Customer Name:</strong> {order_data.get('fname') + " " + order_data.get('lname')}</p>
                    <p><strong>Customer Email: </strong> {order_data.get('email')} </p>
                    <p><strong>Phone: </strong> {order_data.get('phone')} </p>
                    <p><strong>Order Reference:</strong> {order_data.get('token')}</p>
                    <p><strong>Shipping Address:</strong> { order_data.get('shipping_address') if order_data.get('order_type') == 'shipping' else 'N/A'}</p>
                    <p><strong>Pickup Details:</strong> {order_data.get('pickup_lookup_address') if order_data.get('order_type') == 'pickup' else 'N/A'}</p>
                    <p>Please process this order as soon as possible.</p>
                  </body>
                </html>
                """
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": config.ADMIN_ORDER_CONFIRMATION_EMAIL
                    }
                },
                {
                    "emailAddress": {
                        "address": config.CONFIRMATION_GMAIL_GOOGLE_PHOTOS
                    }
                }
            ]
        },
        "saveToSentItems": "true"
    }

    # Initialize attachments list
    attachments = []
    
    # Add GCS attachment if image_path is provided
    if digital_photo_name:
        # Add to attachments list
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": digital_photo_name,
            "contentType": digital_content_type,
            "contentBytes": base64.b64encode(digital_image_bytes).decode('utf-8')
        })
    
    if template_photo_name:
        # Add to attachments list
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": template_photo_name,
            "contentType": template_content_type,
            "contentBytes": base64.b64encode(template_image_bytes).decode('utf-8')
        })
    
    # Add attachments to email if any were successfully prepared
    if attachments:
        email_message["message"]["attachments"] = attachments


    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(endpoint, headers=headers, json=email_message)

    if response.status_code == 202:
        print("Admin notification email sent successfully.")
    else:
        print(f"Exception: Failed to send admin notification: {response.status_code} {response.text}")


# Removed get_image_from_gcs function - now using download_file_from_storage from storage_utils


def get_image_from_local_file(file_path):
    """
    Read image data from a local file.
    
    Args:
        file_path: Path to local image file
        
    Returns:
        Tuple of (image_bytes, content_type, filename)
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Local file not found: {file_path}")
        
        # Read file content
        with open(file_path, 'rb') as f:
            image_bytes = f.read()
        
        # Determine content type based on file extension
        filename = os.path.basename(file_path)
        if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif filename.lower().endswith('.png'):
            content_type = 'image/png'
        else:
            content_type = 'application/octet-stream'
            
        return image_bytes, content_type, filename
    except Exception as e:
        print(f"Error reading local image file: {str(e)}")
        raise


