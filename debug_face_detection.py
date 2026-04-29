#!/usr/bin/env python3
import os
import sys
import cv2
import face_recognition
import numpy as np
from PIL import Image
import glob

def test_face_detection(image_path):
    """Test face detection on a single image with various parameters"""
    print(f"\n=== Testing face detection on: {image_path} ===")
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"ERROR: Could not load image {image_path}")
        return
        
    print(f"Image shape: {img.shape}")
    
    # Convert to RGB
    rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Test 1: Default HOG
    print("\n1. Testing HOG model (default)...")
    face_locations = face_recognition.face_locations(rgb_image, model="hog")
    print(f"   Found {len(face_locations)} faces: {face_locations}")
    
    # Test 2: HOG with upsampling
    print("\n2. Testing HOG model with upsampling...")
    face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=2, model="hog")
    print(f"   Found {len(face_locations)} faces: {face_locations}")
    
    # Test 3: CNN model (if available)
    print("\n3. Testing CNN model...")
    try:
        face_locations = face_recognition.face_locations(rgb_image, model="cnn")
        print(f"   Found {len(face_locations)} faces: {face_locations}")
    except Exception as e:
        print(f"   CNN model failed: {e}")
    
    # Test 4: Resize image and try again
    print("\n4. Testing with resized image...")
    height, width = rgb_image.shape[:2]
    if width > 1000 or height > 1000:
        # Resize to max 1000px on largest side
        scale = 1000 / max(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        resized = cv2.resize(rgb_image, (new_width, new_height))
        print(f"   Resized from {width}x{height} to {new_width}x{new_height}")
        
        face_locations = face_recognition.face_locations(resized, model="hog")
        print(f"   Found {len(face_locations)} faces: {face_locations}")
    else:
        print(f"   Image already small enough: {width}x{height}")
    
    # Test 5: Convert to grayscale and enhance contrast
    print("\n5. Testing with contrast enhancement...")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.equalizeHist(gray)
    enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
    
    face_locations = face_recognition.face_locations(enhanced_rgb, model="hog")
    print(f"   Found {len(face_locations)} faces: {face_locations}")

if __name__ == "__main__":
    # Test with any images in /tmp that might be debug images
    test_images = glob.glob("/tmp/debug_image_*.jpg")
    
    if not test_images:
        print("No debug images found in /tmp/")
        print("Try taking a photo through the app first to generate debug images")
    else:
        for img_path in test_images:
            test_face_detection(img_path)
    
    # Also test with any images in current directory
    local_images = glob.glob("*.jpg") + glob.glob("*.jpeg") + glob.glob("*.png")
    for img_path in local_images:
        test_face_detection(img_path)
