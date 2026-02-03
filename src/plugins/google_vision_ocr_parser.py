"""
Google Cloud Vision OCR Parser

Uses Google Cloud Vision API for document OCR and text detection.
Google Cloud Vision is widely recognized as one of the best OCR services available.
"""

import os
import time
from pathlib import Path
from typing import Any

import fitz
from google.cloud import vision
from google.oauth2 import service_account

from src.plugins.document_processor_base import BaseDocumentProcessor, DocumentParserException
from src.utils import logger


class GoogleVisionOCRParser(BaseDocumentProcessor):
    """Google Cloud Vision OCR Parser"""

    def __init__(self, credentials_path: str | None = None, credentials_json: str | None = None):
        """
        Initialize Google Cloud Vision OCR Parser

        Args:
            credentials_path: Path to service account JSON file
            credentials_json: JSON string of service account credentials
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.credentials_json = credentials_json or os.getenv("GOOGLE_CREDENTIALS_JSON")

        if not self.credentials_path and not self.credentials_json:
            raise DocumentParserException(
                "Google Cloud credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_CREDENTIALS_JSON",
                self.get_service_name(),
                "missing_credentials",
            )

        self.client = None

    def get_service_name(self) -> str:
        return "google_vision_ocr"

    def get_supported_extensions(self) -> list[str]:
        """Google Cloud Vision supports PDF and various image formats"""
        return [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"]

    def _get_client(self) -> vision.ImageAnnotatorClient:
        """Lazy load the Vision API client"""
        if self.client is not None:
            return self.client

        try:
            if self.credentials_json:
                import json

                credentials_dict = json.loads(self.credentials_json)
                credentials = service_account.Credentials.from_service_account_info(credentials_dict)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
            elif self.credentials_path:
                if not os.path.exists(self.credentials_path):
                    raise DocumentParserException(
                        f"Credentials file not found: {self.credentials_path}",
                        self.get_service_name(),
                        "credentials_not_found",
                    )
                credentials = service_account.Credentials.from_service_account_file(self.credentials_path)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
            else:
                self.client = vision.ImageAnnotatorClient()

            logger.info("Google Cloud Vision client initialized")
            return self.client

        except Exception as e:
            raise DocumentParserException(
                f"Failed to initialize Google Cloud Vision client: {str(e)}",
                self.get_service_name(),
                "client_init_failed",
            )

    def check_health(self) -> dict[str, Any]:
        """Check Google Cloud Vision API availability"""
        try:
            client = self._get_client()

            import io

            from PIL import Image

            test_image = Image.new("RGB", (100, 100), color="white")
            img_byte_arr = io.BytesIO()
            test_image.save(img_byte_arr, format="PNG")
            img_byte_arr.seek(0)

            image = vision.Image(content=img_byte_arr.read())
            client.text_detection(image=image)

            return {
                "status": "healthy",
                "message": "Google Cloud Vision API is available",
                "details": {"service": "Google Cloud Vision OCR"},
            }

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "permission" in error_str.lower():
                return {
                    "status": "unhealthy",
                    "message": "Google Cloud Vision API permission denied. Check credentials and API enablement.",
                    "details": {"error": error_str},
                }
            elif "401" in error_str or "authentication" in error_str.lower():
                return {
                    "status": "unhealthy",
                    "message": "Google Cloud Vision API authentication failed. Check credentials.",
                    "details": {"error": error_str},
                }
            else:
                return {
                    "status": "error",
                    "message": f"Google Cloud Vision API health check failed: {error_str}",
                    "details": {"error": error_str},
                }

    def _process_image_bytes(self, image_bytes: bytes) -> str:
        """Process image bytes and extract text using Google Cloud Vision"""
        try:
            client = self._get_client()
            image = vision.Image(content=image_bytes)

            response = client.document_text_detection(image=image)

            if response.error.message:
                raise DocumentParserException(
                    f"Google Vision API error: {response.error.message}",
                    self.get_service_name(),
                    "api_error",
                )

            if response.full_text_annotation:
                return response.full_text_annotation.text

            texts = response.text_annotations
            if texts:
                return texts[0].description

            return ""

        except DocumentParserException:
            raise
        except Exception as e:
            raise DocumentParserException(
                f"Image processing failed: {str(e)}", self.get_service_name(), "processing_failed"
            )

    def _process_image_file(self, file_path: str) -> str:
        """Process a single image file"""
        with open(file_path, "rb") as f:
            content = f.read()
        return self._process_image_bytes(content)

    def _process_pdf(self, file_path: str, params: dict[str, Any] | None = None) -> str:
        """
        Process PDF by converting pages to images and OCR each page

        Args:
            file_path: PDF file path
            params: Processing parameters
                - dpi: DPI for PDF rendering (default: 200)
                - max_pages: Maximum number of pages to process (default: None)
        """
        params = params or {}
        dpi = params.get("dpi", 200)
        max_pages = params.get("max_pages")

        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)

            if max_pages:
                total_pages = min(total_pages, max_pages)

            logger.info(f"Processing PDF with {total_pages} pages using Google Cloud Vision")

            all_text = []
            for page_num in range(total_pages):
                page = doc[page_num]

                pix = page.get_pixmap(dpi=dpi)
                img_bytes = pix.tobytes("png")

                page_text = self._process_image_bytes(img_bytes)
                all_text.append(page_text)

                if (page_num + 1) % 10 == 0:
                    logger.info(f"Processed {page_num + 1}/{total_pages} pages")

            doc.close()
            return "\n\n".join(all_text)

        except DocumentParserException:
            raise
        except Exception as e:
            raise DocumentParserException(
                f"PDF processing failed: {str(e)}", self.get_service_name(), "pdf_processing_failed"
            )

    def process_file(self, file_path: str, params: dict[str, Any] | None = None) -> str:
        """
        Process file using Google Cloud Vision OCR

        Args:
            file_path: File path
            params: Processing parameters
                - dpi: DPI for PDF rendering (default: 200)
                - max_pages: Maximum number of pages to process for PDFs (default: None)

        Returns:
            str: Extracted text content
        """
        if not os.path.exists(file_path):
            raise DocumentParserException(f"File not found: {file_path}", self.get_service_name(), "file_not_found")

        file_ext = Path(file_path).suffix.lower()
        if not self.supports_file_type(file_ext):
            raise DocumentParserException(
                f"Unsupported file type: {file_ext}", self.get_service_name(), "unsupported_file_type"
            )

        try:
            start_time = time.time()
            logger.info(f"Google Cloud Vision OCR starting: {os.path.basename(file_path)}")

            if file_ext == ".pdf":
                text = self._process_pdf(file_path, params)
            else:
                text = self._process_image_file(file_path)

            processing_time = time.time() - start_time
            logger.info(
                f"Google Cloud Vision OCR finished: {os.path.basename(file_path)} - {len(text)} chars ({processing_time:.2f}s)"
            )

            return text

        except DocumentParserException:
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Google Cloud Vision OCR failed: {str(e)}"
            logger.error(f"{error_msg} ({processing_time:.2f}s)")
            raise DocumentParserException(error_msg, self.get_service_name(), "processing_failed")
