from google.cloud import storage
import google.auth
from google.auth.transport.requests import Request
import datetime
import os
from utils.process_images import generate_composite_image
from config import STORAGE_BUCKET

def _generate_download_url(blob, expiration_hours=1):
    expiration = datetime.timedelta(hours=expiration_hours)

    try:
        # Works with JSON key credentials (local/dev) and some SA creds.
        return blob.generate_signed_url(version="v4", expiration=expiration, method="GET")
    except Exception as e:
        # Cloud Run metadata credentials don't expose a private key. Use IAM-based signing.
        if "private key" not in str(e).lower() and "sign credentials" not in str(e).lower():
            raise

        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(Request())
        service_account_email = getattr(credentials, "service_account_email", None)
        if not service_account_email:
            raise

        return blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET",
            service_account_email=service_account_email,
            access_token=credentials.token,
        )

def upload_file_to_storage(local_file_path, destination_blob_name):
    """
    Uploads a file to Google Cloud Storage and returns the public URL.
    Assumes service account credentials are set via the environment variable
    GOOGLE_APPLICATION_CREDENTIALS or are otherwise available.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(STORAGE_BUCKET)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    # Optionally, make the file public. Uncomment if desired:
    # blob.make_public()
    # print("Bucket name:", bucket_name, type(bucket_name))
    # print("Destination blob name:", destination_blob_name, type(destination_blob_name))
    url = _generate_download_url(blob)
    # url = blob.public_url
    # print("URL", url)
    return url

def upload_images(token, selected_layout):
    """
    Uploads the processed image and composite image to google storage.
    Returns a tuple: (processed_storage_url, composite_storage_url)
    """
    processed_image_path = f"/tmp/processed_{token}.jpg"
    if not os.path.exists(processed_image_path):
        raise Exception("Processed image not found. Complete the image processing step first.")

    # Read document type for canvas selection
    doc_type = 'default'  # Default fallback
    doc_type_filename = f"/tmp/doc_type_{token}.txt"
    if os.path.exists(doc_type_filename):
        try:
            with open(doc_type_filename, 'r') as f:
                doc_type = f.read().strip()
                print(f"[DEBUG] Retrieved document type: {doc_type} for token: {token}")
        except Exception as e:
            print(f"[WARNING] Could not read document type file: {e}. Using default.")
    else:
        print(f"[WARNING] Document type file not found for token: {token}. Using default.")

    processed_storage_url = upload_file_to_storage(
        processed_image_path,
        f"orders/{os.path.basename(processed_image_path)}"
    )
    try:
        composite_image_path = generate_composite_image(processed_image_path, selected_layout, doc_type)
    except Exception as e:
        raise Exception("Composite image generation failed: " + str(e))
    composite_storage_url = upload_file_to_storage(
        composite_image_path,
        f"orders/{os.path.basename(composite_image_path)}"
    )
    
    # Clean up document type file after use
    try:
        if os.path.exists(doc_type_filename):
            os.remove(doc_type_filename)
            print(f"[DEBUG] Cleaned up document type file for token: {token}")
    except Exception as e:
        print(f"[WARNING] Could not clean up document type file: {e}")
    
    return processed_storage_url, composite_storage_url, processed_image_path, composite_image_path

def extract_filename_from_url(url_or_path):
    """
    Extract just the filename from a GCS URL or path.
    
    Args:
        url_or_path: A GCS URL or blob path
        
    Returns:
        The extracted filename
    """
    if url_or_path.startswith('https://storage.googleapis.com/'):
        # Extract the filename from the URL path (before any query parameters)
        import re
        match = re.search(r'/orders/([^/?]+)', url_or_path)
        if match:
            # Get just the filename from the match
            filename = match.group(1)
            print(f"Extracted filename from URL: {filename}")
            return filename
        else:
            # Fallback if regex doesn't match
            print(f"Error extracting filename from URL: {url_or_path}")
            raise Exception(f"Error extracting filename: Unable to parse URL: {url_or_path}")
    else:
        # It's already a filename or path
        return os.path.basename(url_or_path)

def download_file_from_storage(blob_name_or_url):
    """
    Downloads a file from Google Cloud Storage and returns its contents as bytes.
    Uses the same authentication as upload_file_to_storage.
    
    Args:
        blob_name_or_url: Name of the blob in the bucket to download or a full GCS signed URL
        
    Returns:
        Tuple of (file_bytes, content_type)
    """
    blob_name = blob_name_or_url
        
    # Remove any leading slashes
    if blob_name.startswith('/'):
        blob_name = blob_name[1:]
    
    # For GCS, we need to use the full path correctly
    full_path = f"orders/{blob_name}"
    print(f"Attempting to download from GCS: {full_path}")
    
    # Get the storage client and bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(STORAGE_BUCKET)
    
    # Get the blob and its contents
    blob = bucket.blob(full_path)
    
    try:
        # Get file content
        file_bytes = blob.download_as_bytes()
        
        # Determine content type based on file extension
        filename = os.path.basename(blob_name)
        if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif filename.lower().endswith('.png'):
            content_type = 'image/png'
        else:
            content_type = 'application/octet-stream'
        
        return file_bytes, content_type
    except Exception as e:
        print(f"Error downloading from GCS: {e}")
        raise
