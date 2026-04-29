import pillow_heif
from PIL import Image, ExifTags
import io
import cv2
import numpy as np
import time

# Initialize Pillow for HEIF support
pillow_heif.register_heif_opener()

def correct_image_orientation(pil_image):
    """
    Correct image orientation based on EXIF data.
    """
    try:
        # Get EXIF data
        exif = pil_image._getexif()
        if exif is not None:
            # Find orientation tag
            for tag, value in exif.items():
                if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                    orientation = value
                    print(f"[DEBUG] EXIF Orientation: {orientation}")
                    
                    # Apply rotation based on orientation
                    if orientation == 2:
                        pil_image = pil_image.transpose(Image.FLIP_LEFT_RIGHT)
                    elif orientation == 3:
                        pil_image = pil_image.rotate(180, expand=True)
                    elif orientation == 4:
                        pil_image = pil_image.rotate(180, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                    elif orientation == 5:
                        pil_image = pil_image.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                    elif orientation == 6:
                        pil_image = pil_image.rotate(-90, expand=True)
                    elif orientation == 7:
                        pil_image = pil_image.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                    elif orientation == 8:
                        pil_image = pil_image.rotate(90, expand=True)
                    break
    except Exception as e:
        print(f"[DEBUG] Could not read EXIF data: {e}")
    
    return pil_image

def load_image(file, filename):
    """
    Load an image from an uploaded file. Supports HEIC conversion and EXIF orientation correction.
    Returns an OpenCV BGR image.
    """
    file_bytes = file.read()
    file.seek(0)
    
    print(f"[DEBUG] Loading image: {filename}")
    
    if filename.lower().endswith('.heic'):
        heif_file = pillow_heif.read_heif(file_bytes)
        pil_image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride
        )
    else:
        pil_image = Image.open(io.BytesIO(file_bytes))
        print(f"[DEBUG] Loaded image mode: {pil_image.mode}, size: {pil_image.size}")
    
    # Correct orientation based on EXIF data
    pil_image = correct_image_orientation(pil_image)
    print(f"[DEBUG] Image size after orientation correction: {pil_image.size}")
    
    # Convert to RGB then to OpenCV BGR format
    rgb_image = pil_image.convert("RGB")
    np_image = np.array(rgb_image)
    bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
    
    print(f"[DEBUG] Final BGR image shape: {bgr_image.shape}")
    return bgr_image
