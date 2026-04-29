#!/usr/bin/env python
"""
Google Cloud Storage to Google Photos Uploader

This module provides functionality to upload photos from Google Cloud Storage
to Google Photos using the Google Photos Library API.
"""
import io
import os
import pickle
import time
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from google.auth.transport.requests import AuthorizedSession

# Define the required scopes for Google Photos API
SCOPES = ['https://www.googleapis.com/auth/photoslibrary',
          'https://www.googleapis.com/auth/photoslibrary.sharing']

# Path to store credentials
TOKEN_PATH = Path.home() / '.credentials' / 'google_photos_token.pickle'
CREDENTIALS_PATH = Path.home() / '.credentials' / 'google_photos_credentials.json'

class GCSToPhotosUploader:
    """Class to handle uploading photos from Google Cloud Storage to Google Photos."""
    
    def __init__(
        self, 
        gcs_bucket_name: str, 
        credentials_path: Optional[str] = None, 
        token_path: Optional[str] = None
    ):
        """
        Initialize the uploader.
        
        Args:
            gcs_bucket_name: Name of the Google Cloud Storage bucket
            credentials_path: Path to the Google Photos API credentials JSON file
            token_path: Path to store/retrieve the Google Photos API token
        """
        self.gcs_bucket_name = gcs_bucket_name
        self.credentials_path = Path(credentials_path) if credentials_path else CREDENTIALS_PATH
        self.token_path = Path(token_path) if token_path else TOKEN_PATH
        
        # Initialize Google Cloud Storage client
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(gcs_bucket_name)
        
        # Ensure credentials directory exists
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize Google Photos API client
        self.photos_service = self._authenticate_google_photos()
    
    def _authenticate_google_photos(self):
        """
        Authenticate with Google Photos API.
        
        Returns:
            Google Photos API service
        """
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Google Photos API credentials not found at {self.credentials_path}. "
                f"Please download OAuth 2.0 Client ID credentials from Google Cloud Console."
            )
        
        # The Google Photos API requires OAuth 2.0 user authentication
        # Service accounts cannot be used directly with Google Photos API for personal accounts
        raise ValueError(
            "Google Photos API requires OAuth 2.0 user authentication. "
            "Service accounts cannot access Google Photos API directly. "
            "You need to create OAuth 2.0 Client ID credentials (Desktop/Web application type) "
            "from Google Cloud Console and use that instead."
        )
        
        # Note: To implement OAuth 2.0 authentication, you would use the following code:
        # from google_auth_oauthlib.flow import InstalledAppFlow
        # from google.oauth2.credentials import Credentials
        # from google.auth.transport.requests import Request
        # 
        # flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
        # creds = flow.run_local_server(port=0)
        # return build('photoslibrary', 'v1', credentials=creds, static_discovery=False)
    
    def list_gcs_objects(self, prefix: Optional[str] = None) -> List[str]:
        """
        List objects in the GCS bucket with optional prefix.
        
        Args:
            prefix: Optional prefix to filter objects
            
        Returns:
            List of object names
        """
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
    
    def download_from_gcs(self, blob_name: str) -> bytes:
        """
        Download an object from GCS.
        
        Args:
            blob_name: Name of the blob to download
            
        Returns:
            Bytes of the downloaded object
        """
        blob = self.bucket.blob(blob_name)
        return blob.download_as_bytes()
    
    def create_album(self, title: str) -> Dict[str, Any]:
        """
        Create a new album in Google Photos.
        
        Args:
            title: Title for the new album
            
        Returns:
            Album information as a dictionary
        """
        try:
            response = self.photos_service.albums().create(
                body={'album': {'title': title}}
            ).execute()
            return response
        except HttpError as error:
            print(f"Error creating album: {error}")
            raise
    
    def list_albums(self) -> List[Dict[str, Any]]:
        """
        List existing albums in Google Photos.
        
        Returns:
            List of album information
        """
        try:
            response = self.photos_service.albums().list(
                pageSize=50
            ).execute()
            
            albums = response.get('albums', [])
            next_page_token = response.get('nextPageToken')
            
            # Fetch additional pages if available
            while next_page_token:
                response = self.photos_service.albums().list(
                    pageSize=50,
                    pageToken=next_page_token
                ).execute()
                albums.extend(response.get('albums', []))
                next_page_token = response.get('nextPageToken')
            
            return albums
        except HttpError as error:
            print(f"Error listing albums: {error}")
            raise
    
    def upload_media_item(self, image_bytes: bytes, filename: str) -> str:
        """
        Upload a media item to Google Photos.
        
        Args:
            image_bytes: The bytes of the image
            filename: The filename to use
            
        Returns:
            The upload token for the media item
        """
        try:
            # The Photos API doesn't use the standard media upload pattern
            # Instead, we upload the bytes directly to the uploadMediaItem endpoint
            upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
            headers = {
                'Content-Type': 'application/octet-stream',
                'X-Goog-Upload-File-Name': filename,
                'X-Goog-Upload-Protocol': 'raw'
            }
            
            # Use the authorized session for the upload
            response = self.authorized_session.post(
                upload_url,
                data=image_bytes,
                headers=headers
            )
            
            if response.status_code != 200:
                error_msg = f"Upload failed with status {response.status_code}: {response.text}"
                print(error_msg)
                raise Exception(error_msg)
                
            return response.text
        except Exception as error:
            print(f"Error uploading media item: {error}")
            raise
    
    def create_media_items(
        self, 
        upload_tokens: List[str], 
        album_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Create media items in Google Photos from upload tokens.
        
        Args:
            upload_tokens: List of upload tokens from upload_media_item
            album_id: Optional album ID to add the media items to
            description: Optional description for the media items
            
        Returns:
            List of created media items
        """
        try:
            new_media_items = [
                {
                    'simpleMediaItem': {'uploadToken': token},
                    'description': description or ''
                }
                for token in upload_tokens
            ]
            
            request_body = {'newMediaItems': new_media_items}
            
            # If an album ID was provided, add to that album
            if album_id:
                request_body['albumId'] = album_id
                response = self.photos_service.mediaItems().batchCreate(
                    body=request_body
                ).execute()
            else:
                # Otherwise just add to the user's library
                response = self.photos_service.mediaItems().batchCreate(
                    body=request_body
                ).execute()
            
            return response.get('newMediaItemResults', [])
        except HttpError as error:
            print(f"Error creating media items: {error}")
            raise
    
    def upload_gcs_photos_to_album(
        self, 
        gcs_blob_names: List[str], 
        album_title: Optional[str] = None,
        album_id: Optional[str] = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Upload photos from GCS to a Google Photos album.
        
        Args:
            gcs_blob_names: List of GCS blob names to upload
            album_title: Title for a new album (if album_id is not provided)
            album_id: ID of an existing album
            batch_size: Number of photos to upload in each batch
            
        Returns:
            Dictionary with upload results
        """
        # Create a new album if album_id is not provided
        if not album_id and album_title:
            album = self.create_album(album_title)
            album_id = album['id']
            print(f"Created new album: {album_title} (ID: {album_id})")
        
        total_photos = len(gcs_blob_names)
        successful_uploads = 0
        failed_uploads = 0
        media_items = []
        
        # Process in batches
        for i in range(0, total_photos, batch_size):
            batch_blobs = gcs_blob_names[i:i + batch_size]
            upload_tokens = []
            
            print(f"Processing batch {i // batch_size + 1}/{(total_photos + batch_size - 1) // batch_size}...")
            
            # Upload each photo in the batch
            for blob_name in batch_blobs:
                try:
                    # Extract filename from blob path
                    filename = os.path.basename(blob_name)
                    
                    # Download the image from GCS
                    image_bytes = self.download_from_gcs(blob_name)
                    
                    # Upload to Google Photos and get token
                    upload_token = self.upload_media_item(image_bytes, filename)
                    upload_tokens.append(upload_token)
                    
                    # Add a small delay to avoid rate limits
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Failed to upload {blob_name}: {str(e)}")
                    failed_uploads += 1
            
            # Create media items from upload tokens
            if upload_tokens:
                try:
                    results = self.create_media_items(upload_tokens, album_id)
                    media_items.extend(results)
                    successful_uploads += len([r for r in results if r.get('status', {}).get('code') == 200])
                    
                    # Add a small delay between batches
                    time.sleep(1)
                except Exception as e:
                    print(f"Failed to create media items: {str(e)}")
                    failed_uploads += len(upload_tokens)
        
        return {
            'total_photos': total_photos,
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads,
            'album_id': album_id,
            'media_items': media_items
        }
    
    def upload_folder_to_album(
        self,
        gcs_folder_prefix: str,
        album_title: Optional[str] = None,
        album_id: Optional[str] = None,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Upload all photos from a GCS folder to a Google Photos album.
        
        Args:
            gcs_folder_prefix: Prefix (folder) in GCS to upload from
            album_title: Title for a new album (if album_id is not provided)
            album_id: ID of an existing album
            batch_size: Number of photos to upload in each batch
            
        Returns:
            Dictionary with upload results
        """
        # List all objects in the GCS folder
        blob_names = self.list_gcs_objects(prefix=gcs_folder_prefix)
        
        # Filter to include only image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif']
        image_blob_names = [
            name for name in blob_names 
            if any(name.lower().endswith(ext) for ext in image_extensions)
        ]
        
        if not image_blob_names:
            return {
                'total_photos': 0,
                'successful_uploads': 0,
                'failed_uploads': 0,
                'album_id': album_id,
                'media_items': [],
                'error': f"No image files found in GCS folder '{gcs_folder_prefix}'"
            }
        
        print(f"Found {len(image_blob_names)} images in GCS folder '{gcs_folder_prefix}'")
        
        # Upload the images to Google Photos
        return self.upload_gcs_photos_to_album(
            image_blob_names,
            album_title=album_title,
            album_id=album_id,
            batch_size=batch_size
        )

def upload_single_image(uploader: GCSToPhotosUploader, blob_name: str, album_title: Optional[str] = None, album_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Upload a single image from GCS to Google Photos.
    
    Args:
        uploader: GCSToPhotosUploader instance
        blob_name: Name of the GCS blob (image) to upload
        album_title: Title for a new album (if album_id is not provided)
        album_id: ID of an existing album
        
    Returns:
        Dictionary with upload result
    """
    # Create a new album if album_id is not provided
    if not album_id and album_title:
        album = uploader.create_album(album_title)
        album_id = album['id']
        print(f"Created new album: {album_title} (ID: {album_id})")
    
    try:
        # Extract filename from blob path
        filename = os.path.basename(blob_name)
        
        print(f"Uploading image: {blob_name}")
        
        # Download the image from GCS
        image_bytes = uploader.download_from_gcs(blob_name)
        
        # Upload to Google Photos and get token
        upload_token = uploader.upload_media_item(image_bytes, filename)
        
        # Create media item from upload token
        results = uploader.create_media_items([upload_token], album_id)
        
        status = results[0].get('status', {}).get('code') if results else 500
        successful = status == 200
        
        return {
            'successful': successful,
            'album_id': album_id,
            'media_item': results[0] if results else None,
            'error': None if successful else f"Upload failed with status code: {status}"
        }
        
    except Exception as e:
        error_msg = f"Failed to upload {blob_name}: {str(e)}"
        print(error_msg)
        return {
            'successful': False,
            'album_id': album_id,
            'media_item': None,
            'error': error_msg
        }

def main():
    """Main function to demonstrate usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload photos from Google Cloud Storage to Google Photos')
    parser.add_argument('--bucket', required=True, help='GCS bucket name')
    parser.add_argument('--prefix', help='Prefix (folder) in GCS bucket')
    parser.add_argument('--image', help='Single image path in GCS bucket to upload')
    parser.add_argument('--album', help='Title for new album (optional if --album-id is provided)')
    parser.add_argument('--album-id', help='ID of existing album (optional if --album is provided)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for uploads (for folder uploads)')
    parser.add_argument('--credentials', help='Path to Google Photos API credentials')
    parser.add_argument('--token', help='Path to save/load Google Photos API token')
    
    args = parser.parse_args()
    
    if not args.album and not args.album_id:
        print("Error: Either --album or --album-id must be provided")
        parser.print_help()
        return
        
    if not args.prefix and not args.image:
        print("Error: Either --prefix or --image must be provided")
        parser.print_help()
        return
    
    try:
        uploader = GCSToPhotosUploader(
            args.bucket,
            credentials_path=args.credentials,
            token_path=args.token
        )
        
        if args.image:  # Upload a single image
            result = upload_single_image(
                uploader,
                args.image,
                album_title=args.album,
                album_id=args.album_id
            )
            
            print("\nUpload Summary:")
            print(f"Image: {args.image}")
            print(f"Status: {'Success' if result['successful'] else 'Failed'}")
            if result['error']:
                print(f"Error: {result['error']}")
            print(f"Album ID: {result['album_id']}")
        
        else:  # Upload a folder
            result = uploader.upload_folder_to_album(
                args.prefix,
                album_title=args.album,
                album_id=args.album_id,
                batch_size=args.batch_size
            )
            
            print("\nUpload Summary:")
            print(f"Total photos processed: {result['total_photos']}")
            print(f"Successfully uploaded: {result['successful_uploads']}")
            print(f"Failed uploads: {result['failed_uploads']}")
            print(f"Album ID: {result['album_id']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
