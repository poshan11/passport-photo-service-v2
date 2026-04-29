import sys
sys.path.insert(0, "MODNet")
from src.models.modnet import MODNet
import face_recognition
import torch
import cv2
import os
import uuid
from PIL import Image, ImageDraw, ImageFont
from flask import send_file, jsonify
import io
import numpy as np
# Initialize dlib face detector and landmark predictor.
# detector = dlib.get_frontal_face_detector()
# predictor_path = "shape_predictor_68_face_landmarks.dat"
# landmark_predictor = dlib.shape_predictor(predictor_path)

# Set your MODNet checkpoint path.
MODNET_CKPT_PATH = "MODNet/ckpt/modnet_photographic_portrait_matting.ckpt"
#ToDo
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
device = "cpu"

# Document type configurations
# Using 300 DPI as standard for passport photos: 1 inch = 300 pixels, 1mm = ~11.81 pixels
DOCUMENT_CONFIGS = {
    'us_passport': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,  # Head should be 70% of photo height
        'eye_level': 0.6  # Eyes should be at 60% from bottom
    },
    'baby_passport': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.6,  # More lenient for babies
        'eye_level': 0.55
    },
    'canada_passport': {
        'final_width': 591,   # 50mm at 300 DPI (~590.55 pixels)
        'final_height': 827,  # 70mm at 300 DPI (~826.77 pixels)
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'uk_passport': {
        'final_width': 413,   # 35mm at 300 DPI (~413.39 pixels)
        'final_height': 531,  # 45mm at 300 DPI (~531.50 pixels)
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'turkish_passport': {
        'final_width': 591,   # 50mm at 300 DPI
        'final_height': 709,  # 60mm at 300 DPI (~708.66 pixels)
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'vietnam_passport': {
        'final_width': 472,   # 4cm at 300 DPI (~472.44 pixels)
        'final_height': 709,  # 6cm at 300 DPI (~708.66 pixels)
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'jamaican_passport': {
        'final_width': 413,   # 35mm at 300 DPI
        'final_height': 531,  # 45mm at 300 DPI
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'chinese_visa': {
        'final_width': 390,   # 33mm at 300 DPI (~389.76 pixels)
        'final_height': 567,  # 48mm at 300 DPI (~566.93 pixels)
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'uae_visa': {
        'final_width': 508,   # 43mm at 300 DPI (~508.27 pixels)
        'final_height': 650,  # 55mm at 300 DPI (~649.61 pixels)
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'indian_passport': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'japan_passport': {
        'final_width': 413,   # 35mm at 300 DPI
        'final_height': 531,  # 45mm at 300 DPI
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'french_passport': {
        'final_width': 413,   # 35mm at 300 DPI
        'final_height': 531,  # 45mm at 300 DPI
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'australian_visa': {
        'final_width': 413,   # 35mm at 300 DPI
        'final_height': 531,  # 45mm at 300 DPI
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'us_visa': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'visa_photo': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'real_id': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'uscis': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'green_card': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'ead_card': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'nfa_atf': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'student_id': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'custom_size': {
        'final_width': 600,   # Default dimensions (will be overridden by frontend)
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'usa_REAL_ID': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'usa_passport': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'usa_immigrant_visa': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'usa_nonimmigrant_visa': {
        'final_width': 600,   # 2x2 inches at 300 DPI
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    },
    'default': {
        'final_width': 600,   # Default dimensions
        'final_height': 600,
        'background': 'white',
        'head_ratio': 0.7,
        'eye_level': 0.6
    }
}

def get_document_config(doc_type):
    """Get configuration for a specific document type."""
    return DOCUMENT_CONFIGS.get(doc_type, DOCUMENT_CONFIGS['default'])

def load_modnet(ckpt_path, device):
    modnet = MODNet(backbone_pretrained=False).to(device)
    checkpoint = torch.load(ckpt_path, map_location=device)
    state_dict = {k.replace("module.", ""): v for k, v in checkpoint.items()}
    modnet.load_state_dict(state_dict)
    modnet.eval()
    return modnet

# Load MODNet once at startup.
modnet = load_modnet(MODNET_CKPT_PATH, device)

def composite_on_white(bgra_img):
    """
    Composite BGRA image onto white background.
    """
    b, g, r, a = cv2.split(bgra_img)
    alpha = a.astype(float) / 255.0
    white_bg = np.full(b.shape, 255, dtype=np.uint8)
    b = np.uint8(b * alpha + white_bg * (1 - alpha))
    g = np.uint8(g * alpha + white_bg * (1 - alpha))
    r = np.uint8(r * alpha + white_bg * (1 - alpha))
    return cv2.merge([b, g, r])




def resize_with_aspect_ratio_preservation(image, target_width, target_height):
    """
    Resize image to fit within target dimensions while preserving aspect ratio.
    Centers the image on a white background if needed.
    """
    h, w = image.shape[:2]
    
    # Calculate scaling factors for both dimensions
    scale_w = target_width / w
    scale_h = target_height / h
    
    # Use the smaller scale to ensure the image fits within the target dimensions
    scale = min(scale_w, scale_h)
    
    # Calculate new dimensions
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    print(f"[DEBUG] Aspect ratio preservation: original {w}x{h}, scaled to {new_w}x{new_h}, target {target_width}x{target_height}")
    
    # Resize the image
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # If the resized image is smaller than target dimensions, center it on a white background
    if new_w < target_width or new_h < target_height:
        # Create white canvas with target dimensions
        canvas = np.full((target_height, target_width, 3), 255, dtype=np.uint8)
        
        # Calculate centering offsets
        offset_x = (target_width - new_w) // 2
        offset_y = (target_height - new_h) // 2
        
        print(f"[DEBUG] Centering image at offset ({offset_x}, {offset_y})")
        
        # Place the resized image on the canvas
        canvas[offset_y:offset_y + new_h, offset_x:offset_x + new_w] = resized
        
        return canvas
    else:
        return resized

def remove_background_modnet(image, modnet, device):
    """
    Remove background using MODNet.
    """
    h_img, w_img = image.shape[:2]
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).resize((512, 512), Image.BILINEAR)
    np_img = np.array(pil_img).astype(np.float32) / 255.0
    img_tensor = torch.from_numpy(np_img).permute(2, 0, 1).unsqueeze(0).to(device)
    with torch.no_grad():
        _, _, matte = modnet(img_tensor, True)
    matte = matte[0, 0].cpu().numpy()
    matte = (matte * 255).astype(np.uint8)
    matte = cv2.resize(matte, (w_img, h_img), interpolation=cv2.INTER_LINEAR)
    b, g, r = cv2.split(image)
    bgra = cv2.merge([b, g, r, matte])
    return bgra

def compute_final_crop_region(img, face_landmarks, segmented_img):
    """
    Compute the crop region dynamically:
      - Vertical:
          * Top is set to 50px above the hairline (from alpha channel).
          * Bottom is (chin + dynamic padding) based on distance from eye center to chin.
      - Horizontal:
          * We produce a square region centered on the chin X coordinate.
    """
    h_img, w_img = img.shape[:2]
    alpha = segmented_img[:, :, 3]

    # hair rows
    hair_rows = np.where(alpha > 0)[0]
    hair_top = np.min(hair_rows) if hair_rows.size > 0 else 0
    crop_top = max(0, hair_top - 50)

    # The 'chin' list from face_landmarks is from left to right
    chin_points = face_landmarks["chin"]
    # The midpoint of the chin array is effectively the bottom center
    mid_chin_index = len(chin_points) // 2
    chin_x, chin_y = chin_points[mid_chin_index]

    # Eye center:
    left_eye_points = face_landmarks["left_eye"]
    right_eye_points = face_landmarks["right_eye"]
    left_eye_y = np.mean([pt[1] for pt in left_eye_points])
    right_eye_y = np.mean([pt[1] for pt in right_eye_points])
    eye_center_y = (left_eye_y + right_eye_y) / 2.0

    # Dynamic padding
    padding = chin_y - eye_center_y
    crop_bottom = min(h_img, int(chin_y + padding))

    square_size = crop_bottom - crop_top

    # Horizontal boundaries: center around chin_x
    crop_left = int(chin_x - square_size / 2)
    crop_right = int(chin_x + square_size / 2)

    if crop_left < 0:
        crop_left = 0
    if crop_right > w_img:
        crop_right = w_img

    return int(crop_left), int(crop_top), int(crop_right), int(crop_bottom)


def compute_final_crop_region_for_document(img, face_landmarks, segmented_img, config):
    """
    Compute the crop region dynamically based on document configuration:
    - Uses the target aspect ratio from config to determine proper crop dimensions
    - Ensures the cropped region matches the target document aspect ratio
    """
    h_img, w_img = img.shape[:2]
    alpha = segmented_img[:, :, 3]
    
    # Get target aspect ratio from config
    target_width = config['final_width']
    target_height = config['final_height']
    target_aspect_ratio = target_width / target_height
    
    print(f"[DEBUG] Target aspect ratio: {target_aspect_ratio:.3f} ({target_width}x{target_height})")

    # Find hair top (same as original logic)
    hair_rows = np.where(alpha > 0)[0]
    hair_top = np.min(hair_rows) if hair_rows.size > 0 else 0
    crop_top = max(0, hair_top - 50)

    # Find chin position (same as original logic)
    chin_points = face_landmarks["chin"]
    mid_chin_index = len(chin_points) // 2
    chin_x, chin_y = chin_points[mid_chin_index]

    # Eye center (same as original logic)
    left_eye_points = face_landmarks["left_eye"]
    right_eye_points = face_landmarks["right_eye"]
    left_eye_y = np.mean([pt[1] for pt in left_eye_points])
    right_eye_y = np.mean([pt[1] for pt in right_eye_points])
    eye_center_y = (left_eye_y + right_eye_y) / 2.0

    # Dynamic padding
    padding = chin_y - eye_center_y
    crop_bottom = min(h_img, int(chin_y + padding))

    # Calculate crop dimensions based on target aspect ratio
    crop_height = crop_bottom - crop_top
    ideal_crop_width = int(crop_height * target_aspect_ratio)
    
    # Check if the ideal crop width fits within the image
    max_available_width = w_img
    crop_width = min(ideal_crop_width, max_available_width)
    
    # If we had to reduce the width, recalculate height to maintain aspect ratio
    if crop_width < ideal_crop_width:
        crop_height = int(crop_width / target_aspect_ratio)
        # Recalculate crop_bottom based on new height
        crop_bottom = min(h_img, crop_top + crop_height)
    
    print(f"[DEBUG] Calculated crop dimensions: {crop_width}x{crop_height} (aspect ratio: {crop_width/crop_height:.3f})")
    print(f"[DEBUG] Target aspect ratio: {target_aspect_ratio:.3f}")

    # Center horizontally around chin_x
    crop_left = int(chin_x - crop_width / 2)
    crop_right = int(chin_x + crop_width / 2)

    # Ensure boundaries are within image limits
    if crop_left < 0:
        crop_left = 0
        crop_right = crop_width
    if crop_right > w_img:
        crop_right = w_img
        crop_left = w_img - crop_width
        
    # Final boundary check
    crop_left = max(0, crop_left)
    crop_right = min(w_img, crop_right)
    
    # Ensure the final crop dimensions are correct
    actual_crop_width = crop_right - crop_left
    actual_crop_height = crop_bottom - crop_top
    print(f"[DEBUG] Final crop region: {actual_crop_width}x{actual_crop_height} (aspect ratio: {actual_crop_width/actual_crop_height:.3f})")

    return int(crop_left), int(crop_top), int(crop_right), int(crop_bottom)


def preprocess_image_for_face_detection(img):
    """
    Preprocess image to improve face detection reliability.
    """
    height, width = img.shape[:2]
    original_img = img.copy()
    
    # Resize if image is too large (face detection works better on smaller images)
    max_dimension = 1200
    if width > max_dimension or height > max_dimension:
        scale = max_dimension / max(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"[DEBUG] Resized image for face detection: {width}x{height} -> {new_width}x{new_height}")
        return img, original_img, scale
    
    return img, original_img, 1.0

def process_image_array(img, doc_config=None, doc_type='default'):
    """
    Process an image (numpy array) based on document configuration to produce an output:
    - Remove background with MODNet.
    - Detect faces with face_recognition.
    - Adjust processing based on document configuration requirements.
    
    Args:
        img: Input image as numpy array
        doc_config: Dictionary containing document configuration (preferred)
        doc_type: Fallback document type string (for backward compatibility)
    """
    # Use provided config or fall back to hardcoded config
    if doc_config:
        config = doc_config
    else:
        config = get_document_config(doc_type)
    
    print(f"[DEBUG] Processing image for document type: {doc_type if not doc_config else 'custom config'}")
    print(f"[DEBUG] Target dimensions: {config['final_width']}x{config['final_height']} pixels")
    
    # 1. Remove background
    segmented_img = remove_background_modnet(img, modnet, device)

    # 2. Face detection with face_recognition
    print(f"[DEBUG] Input image shape: {img.shape}")
    rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    print(f"[DEBUG] RGB image shape: {rgb_image.shape}")
    
    # Try multiple face detection models and parameters
    face_locations = face_recognition.face_locations(rgb_image, model="hog")
    print(f"[DEBUG] HOG model detected {len(face_locations)} faces")
    
    if len(face_locations) == 0:
        # Try CNN model as fallback
        print("[DEBUG] Trying CNN model as fallback...")
        face_locations = face_recognition.face_locations(rgb_image, model="cnn")
        print(f"[DEBUG] CNN model detected {len(face_locations)} faces")
    
    if len(face_locations) == 0:
        # Try with different number_of_times_to_upsample
        print("[DEBUG] Trying with upsampling...")
        face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=2, model="hog")
        print(f"[DEBUG] HOG with upsampling detected {len(face_locations)} faces")
    
    print(f"[DEBUG] Final face locations: {face_locations}")
    
    if len(face_locations) != 1:
        # Save debug image to see what we're working with
        debug_filename = f"/tmp/debug_image_{uuid.uuid4()}.jpg"
        cv2.imwrite(debug_filename, img)
        print(f"[DEBUG] Saved debug image to: {debug_filename}")
        
        if len(face_locations) == 0:
            raise ValueError(f"No face detected in the image. Debug image saved to {debug_filename}. Please ensure there is a clear, well-lit face in the photo.")
        else:
            raise ValueError(f"Multiple faces detected ({len(face_locations)}). Please ensure only one face is visible in the photo.")

    # 3. Landmarks
    face_landmarks_list = face_recognition.face_landmarks(rgb_image)
    if len(face_landmarks_list) != 1:
        raise ValueError("Photo must contain exactly one face, please re-upload photo with a single face.")
    face_landmarks = face_landmarks_list[0]

    # 4. Use document-specific configuration for processing
    # Use exact dimensions provided by the frontend
    final_width = config['final_width']
    final_height = config['final_height']

    # Compute final crop region (adjusted for document type if needed)
    crop_left, crop_top, crop_right, crop_bottom = compute_final_crop_region_for_document(
        img, face_landmarks, segmented_img, config
    )
    cropped_segmented = segmented_img[crop_top:crop_bottom, crop_left:crop_right]
    
    print(f"[DEBUG] Cropped region dimensions: {crop_right - crop_left}x{crop_bottom - crop_top} pixels")

    # Composite on background (currently only white supported)
    if config['background'] == 'white':
        composite_img = composite_on_white(cropped_segmented)
    else:
        # Future: add support for other backgrounds
        composite_img = composite_on_white(cropped_segmented)

    # Use aspect ratio preserving resize to prevent distortion
    final_img = resize_with_aspect_ratio_preservation(composite_img, final_width, final_height)
    
    print(f"[DEBUG] Final image dimensions: {final_img.shape[1]}x{final_img.shape[0]} pixels")
    return final_img


def add_watermark(temp_filename):
    # Open the image and convert to RGBA.
    img = Image.open(temp_filename).convert("RGBA")
    width, height = img.size

    # Create an overlay for the watermark.
    watermark_overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(watermark_overlay)

    watermark_text = "PREVIEW"
    font_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    font_path = os.path.join(font_dir, 'Roboto-Bold.ttf')
    grid_font = ImageFont.load_default()
    try:
        diag_font_size = int(width * 0.15)
        diag_font = ImageFont.truetype(font_path, diag_font_size)
    except Exception:
        diag_font = ImageFont.load_default()

    try:
        clear_font_size = int(width * 0.08)
        clear_font = ImageFont.truetype(font_path, clear_font_size)
    except Exception:
        clear_font = ImageFont.load_default()

    # Precompute grid dimensions.
    columns, rows = 3, 3
    cell_width = width / columns
    cell_height = height / rows
    watermark_color = (255, 0, 0, 204)  # Red with 80% opacity

    # Draw "PREVIEW" in a 3x3 grid with alternating rotations.
    for row in range(rows):
        for col in range(columns):
            # Measure text size once using grid_font.
            bbox = overlay_draw.textbbox((0, 0), watermark_text, font=grid_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            # Create temporary image for the text.
            text_img = Image.new("RGBA", (text_width, text_height), (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_img)
            text_draw.text((0, 0), watermark_text, font=grid_font, fill=watermark_color)
            # Alternate rotation angle.
            angle = -20 if (row + col) % 2 == 0 else 20
            rotated_text = text_img.rotate(angle, expand=1)
            rw, rh = rotated_text.size
            # Center rotated text in the grid cell.
            x = int(col * cell_width + (cell_width - rw) / 2)
            y = int(row * cell_height + (cell_height - rh) / 2)
            watermark_overlay.paste(rotated_text, (x, y), rotated_text)

    # Add an extra diagonal watermark.
    diag_bbox = overlay_draw.textbbox((0, 0), watermark_text, font=diag_font)
    diag_text_width = diag_bbox[2] - diag_bbox[0]
    diag_text_height = diag_bbox[3] - diag_bbox[1]
    diag_img = Image.new("RGBA", (diag_text_width, diag_text_height), (255, 255, 255, 0))
    diag_draw = ImageDraw.Draw(diag_img)
    diag_draw.text((0, 0), watermark_text, font=diag_font, fill=watermark_color)
    rotated_diag = diag_img.rotate(45, expand=1)
    dx = (width - rotated_diag.width) // 2
    dy = (height - rotated_diag.height) // 2
    watermark_overlay.paste(rotated_diag, (dx, dy), rotated_diag)

    # Add clear text at the top: "This is a preview"
    clear_bbox = overlay_draw.textbbox((0, 0), "This is a preview", font=clear_font)
    clear_text_width = clear_bbox[2] - clear_bbox[0]
    clear_x = (width - clear_text_width) // 2
    clear_y = 30  # fixed offset from top
    overlay_draw.text((clear_x, clear_y), "This is a preview", font=clear_font, fill=watermark_color)

    # Composite the watermark overlay onto the original image.
    watermarked_img = Image.alpha_composite(img, watermark_overlay)

    # Save to a BytesIO and return as JPEG.
    img_io = io.BytesIO()
    watermarked_img.convert("RGB").save(img_io, "JPEG")
    img_io.seek(0)
    return send_file(img_io, mimetype="image/jpeg", as_attachment=False)


def get_background_color_rgb(color_name):
    """
    Get RGB values for common background color names.
    Returns (B, G, R) values for OpenCV (BGR format).
    """
    color_map = {
        'white': (255, 255, 255),        # BGR: White
        'light_blue': (255, 200, 150),   # BGR: Light blue - matches #96C8FF (RGB: 150, 200, 255)
        'blue': (255, 0, 0),             # BGR: Pure blue (RGB: 0, 0, 255)
        'light_gray': (230, 230, 230),   # BGR: Light gray - matches #E6E6E6 (RGB: 230, 230, 230)
        'gray': (128, 128, 128),         # BGR: Medium gray
        'red': (0, 0, 255),              # BGR: Pure red (RGB: 255, 0, 0)
        'light_red': (193, 182, 255),    # BGR: Light pink - matches #FFB6C1 (RGB: 255, 182, 193)
        'green': (0, 255, 0),            # BGR: Pure green (RGB: 0, 255, 0)
        'light_green': (150, 255, 150),  # BGR: Light green
        'yellow': (0, 255, 255),         # BGR: Pure yellow (RGB: 255, 255, 0)
        'light_yellow': (150, 255, 255), # BGR: Light yellow
        'beige': (220, 245, 245),        # BGR: Beige - matches #F5F5DC (RGB: 245, 245, 220)
        'off_white': (250, 245, 245),    # BGR: Off-white - matches #F5F5FA (RGB: 245, 245, 250)
    }
    
    return color_map.get(color_name.lower(), (255, 255, 255))  # Default to white


def change_background_color(image_path, background_color):
    """
    Change the background color of a processed passport photo.
    
    Args:
        image_path: Path to the existing processed image
        background_color: String name of the desired background color
        
    Returns:
        numpy array of the image with changed background
    """
    try:
        print(f"[DEBUG] Changing background color to: {background_color}")
        
        # Load the processed image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image from {image_path}")
            
        print(f"[DEBUG] Image loaded successfully, shape: {img.shape}")
            
        # Get the desired background color
        bg_color = get_background_color_rgb(background_color)
        print(f"[DEBUG] Background RGB color: {bg_color}")
        
        # Improved background detection using multiple methods
        
        # Method 1: Convert to HSV for better color separation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Method 2: Create mask for white/light background pixels
        # Check for high brightness (V channel) and low saturation (S channel)
        brightness_mask = hsv[:, :, 2] > 200  # High brightness
        saturation_mask = hsv[:, :, 1] < 30   # Low saturation (close to white/gray)
        
        # Method 3: Also check in RGB space for near-white pixels
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        white_mask = gray > 230
        
        # Method 4: Check for pixels where all RGB values are high and similar
        b, g, r = cv2.split(img)
        rgb_similarity_mask = (np.abs(b.astype(np.int16) - g.astype(np.int16)) < 20) & \
                              (np.abs(g.astype(np.int16) - r.astype(np.int16)) < 20) & \
                              (b > 200) & (g > 200) & (r > 200)
        
        # Combine all masks for better background detection
        background_mask = (brightness_mask & saturation_mask) | white_mask | rgb_similarity_mask
        
        # Optional: Clean up the mask with morphological operations
        kernel = np.ones((3, 3), np.uint8)
        background_mask = cv2.morphologyEx(background_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
        background_mask = background_mask.astype(bool)
        
        print(f"[DEBUG] Background mask created, {np.sum(background_mask)} pixels will be changed")
        
        # Apply the new background color where the mask indicates background
        result = img.copy()
        result[background_mask] = bg_color
        
        print(f"[DEBUG] Background change completed successfully")
        return result
        
    except Exception as e:
        print(f"[ERROR] Failed to change background color: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise e


def change_background_color_advanced(original_image, background_color, doc_config=None, doc_type='default'):
    """
    Advanced background color change that re-processes the original image with new background.
    This function should be used when we have access to the original image.
    
    Args:
        original_image: Original image as numpy array
        background_color: String name of the desired background color
        doc_config: Document configuration
        doc_type: Document type for fallback
        
    Returns:
        numpy array of the processed image with new background color
    """
    try:
        # Use provided config or fall back to hardcoded config
        if doc_config:
            config = doc_config.copy()
        else:
            config = get_document_config(doc_type).copy()
        
        # Update the background color in config
        config['background'] = background_color
        
        print(f"[DEBUG] Re-processing image with background color: {background_color}")
        
        # 1. Remove background
        segmented_img = remove_background_modnet(original_image, modnet, device)

        # 2. Face detection with face_recognition
        rgb_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image, model="hog")
        if len(face_locations) != 1:
            raise ValueError("No clear face detected, Please re-upload a photo with a face.")

        # 3. Landmarks
        face_landmarks_list = face_recognition.face_landmarks(rgb_image)
        if len(face_landmarks_list) != 1:
            raise ValueError("Photo must contain exactly one face, please re-upload photo with a single face.")
        face_landmarks = face_landmarks_list[0]

        # 4. Use document-specific configuration for processing
        final_width = config['final_width']
        final_height = config['final_height']

        # Compute final crop region
        crop_left, crop_top, crop_right, crop_bottom = compute_final_crop_region_for_document(
            original_image, face_landmarks, segmented_img, config
        )
        cropped_segmented = segmented_img[crop_top:crop_bottom, crop_left:crop_right]
        
        # Composite on the new background color
        composite_img = composite_on_background_color(cropped_segmented, background_color)

        # Resize to final dimensions
        final_img = cv2.resize(composite_img, (final_width, final_height), interpolation=cv2.INTER_LINEAR)
        
        print(f"[DEBUG] Advanced background change completed")
        return final_img
        
    except Exception as e:
        print(f"[ERROR] Advanced background change failed: {str(e)}")
        raise e


def composite_on_background_color(bgra_img, background_color):
    """
    Composite BGRA image onto specified background color.
    
    Args:
        bgra_img: Image with alpha channel (B, G, R, A)
        background_color: String name of background color
        
    Returns:
        BGR image composited on the specified background
    """
    b, g, r, a = cv2.split(bgra_img)
    alpha = a.astype(float) / 255.0
    
    # Get background color
    bg_b, bg_g, bg_r = get_background_color_rgb(background_color)
    
    # Create background with the specified color
    bg_b_layer = np.full(b.shape, bg_b, dtype=np.uint8)
    bg_g_layer = np.full(g.shape, bg_g, dtype=np.uint8)
    bg_r_layer = np.full(r.shape, bg_r, dtype=np.uint8)
    
    # Composite foreground over background
    b = np.uint8(b * alpha + bg_b_layer * (1 - alpha))
    g = np.uint8(g * alpha + bg_g_layer * (1 - alpha))
    r = np.uint8(r * alpha + bg_r_layer * (1 - alpha))
    
    return cv2.merge([b, g, r])


import math

# Standard print sizes in pixels at 300 DPI
CANVAS_PRESETS = {
    '4x6': {'width': 1800, 'height': 1200, 'name': '4"×6"'},  # 4×6 inches at 300 DPI
    '5x7': {'width': 2100, 'height': 1500, 'name': '5"×7"'}   # 5×7 inches at 300 DPI
}

# Document types that use US standard sizing (4x6 canvas)
# Based on frontend countryDocumentData.json USA documents
US_DOCUMENT_TYPES = {
    'default',           # Default document type
    'baby_passport',     # USA baby passport  
    'ead_card',          # Employment Authorization Document
    'green_card',        # Permanent Resident Card
    'nfa_atf',           # NFA/ATF documents
    'real_id',           # Legacy backend name for Real ID
    'student_id',        # Student ID
    'us_passport',       # Legacy backend name for US passport
    'us_visa',           # Legacy backend name for US visa
    'usa_REAL_ID',       # Frontend name with correct casing
    'usa_passport',      # Frontend name for US passport
    'usa_immigrant_visa',     # Frontend name for immigrant visa
    'usa_nonimmigrant_visa',  # Frontend name for nonimmigrant visa
    'uscis',             # USCIS documents
    'visa_photo'         # Visa photo
    # Note: 'custom_size' removed - should use 5x7 for larger flexibility
}

def select_canvas_by_region(doc_type):
    """
    Select canvas size based on document type (region-based).
    
    Args:
        doc_type: Document type string
        
    Returns:
        Canvas size string ('4x6' or '5x7')
    """
    if doc_type in US_DOCUMENT_TYPES:
        return '4x6'  # US documents use 4×6 canvas
    else:
        return '5x7'  # International documents use 5×7 canvas

def calculate_layout_for_canvas(photo_width, photo_height, num_copies, canvas_width, canvas_height):
    """
    Calculate the optimal arrangement of photos on a given canvas.
    
    Args:
        photo_width, photo_height: Dimensions of individual photo
        num_copies: Number of photo copies to arrange
        canvas_width, canvas_height: Canvas dimensions
        
    Returns:
        dict with layout information
    """
    best_layout = None
    best_efficiency = 0
    
    # Try different column arrangements
    for cols in range(1, num_copies + 1):
        rows = math.ceil(num_copies / cols)
        
        # Calculate required canvas size for this arrangement
        required_width = cols * photo_width
        required_height = rows * photo_height
        
        # Check if this arrangement fits in the canvas
        if required_width <= canvas_width and required_height <= canvas_height:
            # Calculate efficiency (how well we use the available space)
            efficiency = (num_copies * photo_width * photo_height) / (canvas_width * canvas_height)
            
            if efficiency > best_efficiency:
                best_efficiency = efficiency
                best_layout = {
                    'cols': cols,
                    'rows': rows,
                    'required_width': required_width,
                    'required_height': required_height,
                    'efficiency': efficiency,
                    'fits': True
                }
    
    if best_layout is None:
        # If nothing fits, return the arrangement anyway for debugging
        cols = min(3, num_copies)  # Limit to 3 columns max
        rows = math.ceil(num_copies / cols)
        best_layout = {
            'cols': cols,
            'rows': rows,
            'required_width': cols * photo_width,
            'required_height': rows * photo_height,
            'efficiency': 0,
            'fits': False
        }
    
    return best_layout

def generate_photo_positions(layout, photo_width, photo_height, canvas_width, canvas_height, num_copies):
    """
    Generate positions for photos on the canvas with centering.
    
    Args:
        layout: Layout information from calculate_layout_for_canvas
        photo_width, photo_height: Individual photo dimensions
        canvas_width, canvas_height: Canvas dimensions
        num_copies: Number of copies to place
        
    Returns:
        List of (x, y) positions for each photo
    """
    cols = layout['cols']
    rows = layout['rows']
    
    # Calculate centering offsets
    total_content_width = cols * photo_width
    total_content_height = rows * photo_height
    
    offset_x = (canvas_width - total_content_width) // 2
    offset_y = (canvas_height - total_content_height) // 2
    
    positions = []
    
    for i in range(num_copies):
        row = i // cols
        col = i % cols
        
        x = offset_x + col * photo_width
        y = offset_y + row * photo_height
        
        positions.append((x, y))
    
    return positions

def generate_composite_image(processed_image_path, selected_layout, doc_type='default'):
    """
    Generates a composite image using region-based canvas selection.
    
    Args:
        processed_image_path: Path to the processed individual photo
        selected_layout: String indicating number of copies ('1', '2', '4', '6', etc.)
        doc_type: Document type to determine canvas size (default: 'default')
        
    Returns:
        Path to the generated composite image
    """
    from PIL import ImageDraw
    
    # Load the individual photo
    img = Image.open(processed_image_path)
    photo_width, photo_height = img.size
    num_copies = int(selected_layout)
    
    print(f"[DEBUG] Generating composite: {num_copies} copies of {photo_width}x{photo_height} photo")
    print(f"[DEBUG] Document type: {doc_type}")
    
    # Select canvas based on document region
    canvas_size = select_canvas_by_region(doc_type)
    canvas_info = CANVAS_PRESETS[canvas_size]
    
    print(f"[DEBUG] Selected canvas: {canvas_info['name']} ({canvas_info['width']}x{canvas_info['height']}) for {doc_type}")
    
    # Calculate layout for the selected canvas
    layout = calculate_layout_for_canvas(
        photo_width, photo_height, num_copies,
        canvas_info['width'], canvas_info['height']
    )
    
    if not layout['fits']:
        print(f"[WARNING] {num_copies} copies of {photo_width}x{photo_height} photo may not fit optimally on {canvas_info['name']} canvas")
        print(f"[WARNING] Required: {layout['required_width']}x{layout['required_height']}, Available: {canvas_info['width']}x{canvas_info['height']}")
    
    print(f"[DEBUG] Layout: {layout['cols']}x{layout['rows']} arrangement, efficiency: {layout['efficiency']:.2%}")
    
    # Create the canvas
    canvas = Image.new('RGB', (canvas_info['width'], canvas_info['height']), 'white')
    draw = ImageDraw.Draw(canvas)
    
    # Generate photo positions
    positions = generate_photo_positions(
        layout, photo_width, photo_height, 
        canvas_info['width'], canvas_info['height'], 
        num_copies
    )
    
    # Place photos on canvas
    photo_positions = []  # For drawing dotted lines
    for i, (x, y) in enumerate(positions):
        canvas.paste(img, (x, y))
        photo_positions.append((x, y, x + photo_width, y + photo_height))
        print(f"[DEBUG] Placed photo {i+1} at position ({x}, {y})")
    
    # Draw dotted lines between photos (not on outer edges)
    canvas_width, canvas_height = canvas.size
    
    for x0, y0, x1, y1 in photo_positions:
        # Top line - only if not at the top edge of canvas
        if y0 > 0:
            for x in range(x0, x1, 4):
                draw.line([(x, y0), (x + 2, y0)], fill="black", width=1)
        
        # Right line - only if not at the right edge of canvas
        if x1 < canvas_width:
            for y in range(y0, y1, 4):
                draw.line([(x1, y), (x1, y + 2)], fill="black", width=1)
        
        # Bottom line - only if not at the bottom edge of canvas
        if y1 < canvas_height:
            for x in range(x0, x1, 4):
                draw.line([(x, y1), (x + 2, y1)], fill="black", width=1)
        
        # Left line - only if not at the left edge of canvas
        if x0 > 0:
            for y in range(y0, y1, 4):
                draw.line([(x0, y), (x0, y + 2)], fill="black", width=1)
    
    # Save composite image
    composite_path = f"/tmp/composite_{selected_layout}_{canvas_size}_{os.path.basename(processed_image_path)}"
    canvas.save(composite_path)
    
    print(f"[DEBUG] Composite image saved: {composite_path}")
    print(f"[DEBUG] Final canvas size: {canvas_width}x{canvas_height}")
    
    return composite_path
