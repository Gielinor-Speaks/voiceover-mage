# ABOUTME: Pydantic models for structured image data extraction and storage
# ABOUTME: Handles image URLs, metadata, and optional cold storage of image bytes

import hashlib
from datetime import UTC, datetime
from typing import Literal

import httpx
from pydantic import BaseModel, Field, computed_field

from voiceover_mage.lib.logging import get_logger


class ImageMetadata(BaseModel):
    """Metadata about an extracted image."""
    
    file_extension: str = Field(..., description="Image file extension (png, jpg, etc.)")
    estimated_size: int | None = Field(None, description="Estimated file size in bytes from URL analysis")
    image_type: Literal["chathead", "full_body", "icon", "artwork", "unknown"] = Field(
        default="unknown", 
        description="Inferred type of image"
    )
    extraction_confidence: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0, 
        description="Confidence in the image extraction (0.0-1.0)"
    )
    alt_text: str | None = Field(None, description="Alt text from markdown if available")


class ImageExtraction(BaseModel):
    """Structured representation of an extracted image with optional cold storage capability."""
    
    url: str = Field(..., description="Full URL to the image")
    metadata: ImageMetadata = Field(..., description="Image metadata")
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this image was extracted"
    )
    
    # Cold storage fields (optional)
    image_bytes: bytes | None = Field(
        default=None, 
        description="Raw image bytes for cold storage (optional)"
    )
    fetch_attempted: bool = Field(
        default=False, 
        description="Whether we've attempted to fetch the image bytes"
    )
    fetch_success: bool = Field(
        default=False, 
        description="Whether the image fetch was successful"
    )
    fetch_error: str | None = Field(
        default=None, 
        description="Error message if image fetch failed"
    )
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def url_hash(self) -> str:
        """Generate a hash of the URL for deduplication and caching."""
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]
    
    @computed_field  # type: ignore[prop-decorator] 
    @property
    def has_image_data(self) -> bool:
        """Whether this extraction includes the actual image bytes."""
        return self.image_bytes is not None
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_size_kb(self) -> float | None:
        """Size of stored image in KB, if available."""
        if self.image_bytes:
            return len(self.image_bytes) / 1024
        return None

    async def fetch_image_data(
        self, 
        client: httpx.AsyncClient | None = None, 
        max_size_mb: float = 10.0
    ) -> bool:
        """Fetch and store the image bytes from the URL.
        
        Args:
            client: HTTP client to use (optional, will create one if needed)
            max_size_mb: Maximum image size to fetch in MB
            
        Returns:
            True if fetch was successful, False otherwise
        """
        if self.fetch_attempted:
            return self.fetch_success
            
        logger = get_logger(__name__)
        self.fetch_attempted = True
        
        # Create client if not provided
        _client = client or httpx.AsyncClient(
            headers={"User-Agent": "Gielinor-Speaks/1.0 (https://github.com/gielinor-speaks/)"},
            timeout=30.0
        )
        
        try:
            logger.debug("Fetching image data", url=self.url, url_hash=self.url_hash)
            
            # Stream the response to check size before downloading
            async with _client.stream("GET", self.url) as response:
                response.raise_for_status()
                
                # Check content length if provided
                content_length = response.headers.get("content-length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > max_size_mb:
                        self.fetch_error = f"Image too large: {size_mb:.1f}MB > {max_size_mb}MB"
                        logger.warning("Image too large, skipping", url=self.url, size_mb=size_mb)
                        return False
                
                # Read the image data
                image_data = b""
                async for chunk in response.aiter_bytes():
                    image_data += chunk
                    # Check size as we download
                    if len(image_data) > max_size_mb * 1024 * 1024:
                        self.fetch_error = f"Image exceeded size limit during download"
                        logger.warning("Image too large during download", url=self.url)
                        return False
            
            self.image_bytes = image_data
            self.fetch_success = True
            
            # Update metadata with actual info
            self.metadata.estimated_size = len(image_data)
            
            logger.info(
                "Successfully fetched image data",
                url=self.url,
                url_hash=self.url_hash, 
                size_kb=self.image_size_kb
            )
            
            return True
            
        except Exception as e:
            self.fetch_error = str(e)
            self.fetch_success = False
            logger.error(
                "Failed to fetch image data", 
                url=self.url, 
                error=str(e), 
                error_type=type(e).__name__
            )
            return False
            
        finally:
            # Close client if we created it
            if client is None:
                await _client.aclose()

    def to_storage_dict(self) -> dict:
        """Convert to a dictionary suitable for database storage (excluding large bytes field)."""
        data = self.model_dump()
        # Remove large bytes field for main storage
        if "image_bytes" in data:
            data["has_image_bytes"] = data["image_bytes"] is not None
            data["image_bytes_size"] = len(data["image_bytes"]) if data["image_bytes"] else None
            del data["image_bytes"]
        return data


class ImageExtractionSet(BaseModel):
    """A set of images extracted from an NPC page."""
    
    chathead: ImageExtraction | None = Field(None, description="NPC chathead image")
    full_body: ImageExtraction | None = Field(None, description="Full body/artwork image")
    additional: list[ImageExtraction] = Field(
        default_factory=list, 
        description="Additional images found on the page"
    )
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_images(self) -> int:
        """Total number of images in this set."""
        count = len(self.additional)
        if self.chathead:
            count += 1
        if self.full_body:
            count += 1
        return count
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_chathead(self) -> bool:
        """Whether this set has a chathead image."""
        return self.chathead is not None
    
    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_full_body(self) -> bool:
        """Whether this set has a full body image."""
        return self.full_body is not None

    async def fetch_all_images(
        self, 
        client: httpx.AsyncClient | None = None, 
        max_size_mb: float = 10.0
    ) -> dict[str, bool]:
        """Fetch image data for all images in the set.
        
        Args:
            client: HTTP client to use (optional)
            max_size_mb: Maximum size per image in MB
            
        Returns:
            Dictionary mapping image type to success status
        """
        results = {}
        
        if self.chathead:
            results["chathead"] = await self.chathead.fetch_image_data(client, max_size_mb)
            
        if self.full_body:
            results["full_body"] = await self.full_body.fetch_image_data(client, max_size_mb)
            
        for i, img in enumerate(self.additional):
            results[f"additional_{i}"] = await img.fetch_image_data(client, max_size_mb)
            
        return results