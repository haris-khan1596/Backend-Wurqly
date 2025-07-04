import os
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import boto3
from botocore.exceptions import ClientError
from PIL import Image, ImageFilter
import io

from app.core.config import settings


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def save_file(self, file_content: bytes, filename: str, content_type: str = "image/png") -> str:
        """Save file and return the file path/URL"""
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve file content"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        pass
    
    @abstractmethod
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get a URL for accessing the file"""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend"""
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save_file(self, file_content: bytes, filename: str, content_type: str = "image/png") -> str:
        """Save file to local filesystem"""
        file_path = self.base_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return str(file_path.relative_to(self.base_path))
    
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve file from local filesystem"""
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from local filesystem"""
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get URL for local file (returns relative path)"""
        return f"/files/{file_path}"


class S3StorageBackend(StorageBackend):
    """Amazon S3 storage backend"""
    
    def __init__(self, bucket_name: str, access_key: str, secret_key: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    
    async def save_file(self, file_content: bytes, filename: str, content_type: str = "image/png") -> str:
        """Save file to S3"""
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=file_content,
                ContentType=content_type
            )
            return filename
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {e}")
    
    async def get_file(self, file_path: str) -> bytes:
        """Retrieve file from S3"""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=file_path)
            return response['Body'].read()
        except ClientError as e:
            raise FileNotFoundError(f"File not found in S3: {file_path}")
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError:
            return False
    
    async def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get presigned URL for S3 file"""
        try:
            return self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_path},
                ExpiresIn=expires_in
            )
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {e}")


class ScreenshotStorageService:
    """Service for managing screenshot storage with blur functionality"""
    
    def __init__(self, backend: StorageBackend):
        self.backend = backend
    
    def generate_filename(self, user_id: int, extension: str = "png") -> str:
        """Generate unique filename for screenshot"""
        unique_id = str(uuid.uuid4())
        timestamp = str(int(time.time()))
        return f"screenshots/{user_id}/{timestamp}_{unique_id}.{extension}"
    
    def generate_thumbnail_filename(self, original_filename: str) -> str:
        """Generate thumbnail filename from original filename"""
        name, ext = os.path.splitext(original_filename)
        return f"{name}_thumb{ext}"
    
    def apply_blur(self, image_data: bytes, blur_level: int = 5) -> bytes:
        """Apply blur to image based on blur level (0-100)"""
        if blur_level <= 0:
            return image_data
        
        # Convert blur level (0-100) to radius (0-10)
        radius = (blur_level / 100) * 10
        
        image = Image.open(io.BytesIO(image_data))
        blurred_image = image.filter(ImageFilter.GaussianBlur(radius=radius))
        
        output = io.BytesIO()
        blurred_image.save(output, format='PNG')
        return output.getvalue()
    
    def create_thumbnail(self, image_data: bytes, size: Tuple[int, int] = (200, 150)) -> bytes:
        """Create thumbnail from image"""
        image = Image.open(io.BytesIO(image_data))
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
    
    async def save_screenshot(
        self, 
        image_data: bytes, 
        user_id: int, 
        blur_level: int = 0,
        create_thumbnail: bool = True
    ) -> Tuple[str, Optional[str], dict]:
        """
        Save screenshot with optional blur and thumbnail
        Returns: (file_path, thumbnail_path, metadata)
        """
        # Get image metadata
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size
        file_size = len(image_data)
        
        # Apply blur if requested
        if blur_level > 0:
            image_data = self.apply_blur(image_data, blur_level)
        
        # Generate filename and save main image
        filename = self.generate_filename(user_id)
        file_path = await self.backend.save_file(image_data, filename, "image/png")
        
        # Create and save thumbnail if requested
        thumbnail_path = None
        if create_thumbnail:
            thumbnail_data = self.create_thumbnail(image_data)
            thumbnail_filename = self.generate_thumbnail_filename(filename)
            thumbnail_path = await self.backend.save_file(thumbnail_data, thumbnail_filename, "image/png")
        
        metadata = {
            "width": width,
            "height": height,
            "file_size": file_size,
            "is_blurred": blur_level > 0,
            "blur_level": blur_level
        }
        
        return file_path, thumbnail_path, metadata
    
    async def get_screenshot(self, file_path: str) -> bytes:
        """Retrieve screenshot file"""
        return await self.backend.get_file(file_path)
    
    async def get_screenshot_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get URL for accessing screenshot"""
        return await self.backend.get_file_url(file_path, expires_in)
    
    async def delete_screenshot(self, file_path: str, thumbnail_path: Optional[str] = None) -> bool:
        """Delete screenshot and thumbnail"""
        main_deleted = await self.backend.delete_file(file_path)
        
        if thumbnail_path:
            await self.backend.delete_file(thumbnail_path)
        
        return main_deleted


# Factory function to create storage backend based on configuration
def create_storage_backend() -> StorageBackend:
    """Create storage backend based on configuration"""
    storage_type = getattr(settings, 'STORAGE_TYPE', 'local').lower()
    
    if storage_type == 's3':
        return S3StorageBackend(
            bucket_name=settings.S3_BUCKET_NAME,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            region=getattr(settings, 'S3_REGION', 'us-east-1')
        )
    else:
        upload_dir = getattr(settings, 'UPLOAD_DIRECTORY', 'uploads')
        return LocalStorageBackend(upload_dir)


# Global storage service instance
storage_backend = create_storage_backend()
screenshot_storage = ScreenshotStorageService(storage_backend)
