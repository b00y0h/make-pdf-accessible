"""
PDF Preview Generation Service

Converts PDF pages to PNG images for preview functionality.
"""

import io
import logging
from typing import Optional

import boto3
from pdf2image import convert_from_bytes
from PIL import Image

from ..config import settings

logger = logging.getLogger(__name__)


class PreviewService:
    """Service for generating PDF previews"""

    def __init__(self):
        """Initialize preview service with S3 client"""
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.aws_endpoint_url,
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self.bucket = settings.s3_bucket

    def generate_preview_from_s3(
        self,
        s3_key: str,
        output_s3_key: Optional[str] = None,
        page_number: int = 1,
        dpi: int = 150,
        format: str = "PNG",
    ) -> str:
        """
        Generate a preview image from a PDF stored in S3.

        Args:
            s3_key: S3 key of the source PDF
            output_s3_key: S3 key for the output image (auto-generated if not provided)
            page_number: Page number to convert (1-indexed)
            dpi: Resolution for the output image
            format: Output image format (PNG, JPEG)

        Returns:
            S3 key of the generated preview image
        """
        try:
            # Download PDF from S3
            logger.info(f"Downloading PDF from S3: {s3_key}")
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            pdf_bytes = response["Body"].read()

            # Convert PDF to images
            logger.info(f"Converting PDF page {page_number} to {format}")
            images = convert_from_bytes(
                pdf_bytes,
                dpi=dpi,
                first_page=page_number,
                last_page=page_number,
                fmt=format.lower(),
            )

            if not images:
                raise ValueError(f"No image generated for page {page_number}")

            image = images[0]

            # Optionally resize for web display
            max_width = 1200
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save image to bytes
            image_buffer = io.BytesIO()
            image.save(image_buffer, format=format)
            image_buffer.seek(0)

            # Generate output S3 key if not provided
            if not output_s3_key:
                base_key = s3_key.rsplit(".", 1)[0]
                output_s3_key = f"{base_key}_preview_p{page_number}.{format.lower()}"

            # Upload preview to S3
            logger.info(f"Uploading preview to S3: {output_s3_key}")
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=output_s3_key,
                Body=image_buffer.getvalue(),
                ContentType=f"image/{format.lower()}",
                Metadata={
                    "source_pdf": s3_key,
                    "page_number": str(page_number),
                    "dpi": str(dpi),
                },
            )

            return output_s3_key

        except Exception as e:
            logger.error(f"Failed to generate preview: {str(e)}")
            raise

    def generate_preview_from_bytes(
        self,
        pdf_bytes: bytes,
        page_number: int = 1,
        dpi: int = 150,
        format: str = "PNG",
    ) -> bytes:
        """
        Generate a preview image from PDF bytes.

        Args:
            pdf_bytes: PDF file content as bytes
            page_number: Page number to convert (1-indexed)
            dpi: Resolution for the output image
            format: Output image format (PNG, JPEG)

        Returns:
            Image bytes
        """
        try:
            # Convert PDF to images
            images = convert_from_bytes(
                pdf_bytes,
                dpi=dpi,
                first_page=page_number,
                last_page=page_number,
                fmt=format.lower(),
            )

            if not images:
                raise ValueError(f"No image generated for page {page_number}")

            image = images[0]

            # Optionally resize for web display
            max_width = 1200
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save image to bytes
            image_buffer = io.BytesIO()
            image.save(image_buffer, format=format)
            image_buffer.seek(0)

            return image_buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to generate preview: {str(e)}")
            raise

    def generate_thumbnail(
        self,
        s3_key: str,
        output_s3_key: Optional[str] = None,
        size: tuple = (300, 400),
        format: str = "PNG",
    ) -> str:
        """
        Generate a thumbnail image from a PDF.

        Args:
            s3_key: S3 key of the source PDF
            output_s3_key: S3 key for the output thumbnail
            size: Thumbnail size (width, height)
            format: Output image format

        Returns:
            S3 key of the generated thumbnail
        """
        try:
            # Download PDF from S3
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            pdf_bytes = response["Body"].read()

            # Convert first page to image at lower DPI for faster processing
            images = convert_from_bytes(
                pdf_bytes,
                dpi=72,
                first_page=1,
                last_page=1,
                fmt=format.lower(),
            )

            if not images:
                raise ValueError("No image generated for thumbnail")

            image = images[0]

            # Create thumbnail
            image.thumbnail(size, Image.Resampling.LANCZOS)

            # Save thumbnail to bytes
            thumb_buffer = io.BytesIO()
            image.save(thumb_buffer, format=format)
            thumb_buffer.seek(0)

            # Generate output S3 key if not provided
            if not output_s3_key:
                base_key = s3_key.rsplit(".", 1)[0]
                output_s3_key = f"{base_key}_thumb.{format.lower()}"

            # Upload thumbnail to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=output_s3_key,
                Body=thumb_buffer.getvalue(),
                ContentType=f"image/{format.lower()}",
                Metadata={
                    "source_pdf": s3_key,
                    "type": "thumbnail",
                    "width": str(image.width),
                    "height": str(image.height),
                },
            )

            return output_s3_key

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {str(e)}")
            raise


# Singleton instance
preview_service = PreviewService()
