"""
Utility module for input validation, error handling, and security checks.
"""

import base64
import json
import logging
from io import BytesIO
from typing import Tuple, Optional, Dict, Any
import imghdr
from fastapi import HTTPException, status
from config import IMAGE_VALIDATION

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class ImageValidator:
    """Validates image uploads for size, format, and content."""

    ALLOWED_FORMATS = IMAGE_VALIDATION.get('allowed_formats', ['jpeg', 'jpg', 'png'])
    MAX_SIZE_BYTES = IMAGE_VALIDATION.get('max_size_bytes', 5 * 1024 * 1024)
    MIN_WIDTH = IMAGE_VALIDATION.get('min_width', 100)
    MIN_HEIGHT = IMAGE_VALIDATION.get('min_height', 100)
    MAX_WIDTH = IMAGE_VALIDATION.get('max_width', 4096)
    MAX_HEIGHT = IMAGE_VALIDATION.get('max_height', 4096)

    @staticmethod
    def validate_base64_image(base64_data: str) -> bytes:
        """
        Validate and decode base64 image data.

        Args:
            base64_data: Base64 encoded image string

        Returns:
            Decoded image bytes

        Raises:
            ValidationError: If validation fails
        """
        try:
            # Remove data URI prefix if present
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]

            # Decode base64
            image_bytes = base64.b64decode(base64_data)
        except Exception as e:
            logger.warning(f"Base64 decode failed: {str(e)}")
            raise ValidationError("Invalid base64 image data")

        # Check size
        if len(image_bytes) > ImageValidator.MAX_SIZE_BYTES:
            max_mb = ImageValidator.MAX_SIZE_BYTES / (1024 * 1024)
            raise ValidationError(f"Image exceeds maximum size of {max_mb:.1f}MB")

        return image_bytes

    @staticmethod
    def validate_image_format(image_bytes: bytes) -> str:
        """
        Validate image format.

        Args:
            image_bytes: Raw image data

        Returns:
            Image format (jpg, png, etc.)

        Raises:
            ValidationError: If format is invalid or not allowed
        """
        # Use imghdr to detect image type
        image_format = imghdr.what(None, h=image_bytes)

        if image_format is None:
            raise ValidationError("Unable to detect image format. File may be corrupt or not an image.")

        # Normalize format names
        format_map = {'jpeg': 'jpg'}
        normalized_format = format_map.get(image_format, image_format)

        if normalized_format not in ImageValidator.ALLOWED_FORMATS:
            allowed = ', '.join(ImageValidator.ALLOWED_FORMATS)
            raise ValidationError(f"Image format '{normalized_format}' not allowed. Allowed: {allowed}")

        return normalized_format

    @staticmethod
    def validate_image_dimensions(image_bytes: bytes) -> Tuple[int, int]:
        """
        Validate image dimensions using PIL/Pillow.

        Args:
            image_bytes: Raw image data

        Returns:
            Tuple of (width, height)

        Raises:
            ValidationError: If dimensions invalid
        """
        try:
            from PIL import Image
            image = Image.open(BytesIO(image_bytes))
            width, height = image.size
        except Exception as e:
            logger.warning(f"Image dimension check failed: {str(e)}")
            raise ValidationError(f"Unable to verify image dimensions: {str(e)}")

        if width < ImageValidator.MIN_WIDTH or height < ImageValidator.MIN_HEIGHT:
            raise ValidationError(
                f"Image too small. Minimum: {ImageValidator.MIN_WIDTH}x{ImageValidator.MIN_HEIGHT}px, "
                f"Got: {width}x{height}px"
            )

        if width > ImageValidator.MAX_WIDTH or height > ImageValidator.MAX_HEIGHT:
            raise ValidationError(
                f"Image too large. Maximum: {ImageValidator.MAX_WIDTH}x{ImageValidator.MAX_HEIGHT}px, "
                f"Got: {width}x{height}px"
            )

        return width, height

    @staticmethod
    def validate_complete(base64_data: str) -> Tuple[bytes, str, Tuple[int, int]]:
        """
        Perform complete image validation.

        Args:
            base64_data: Base64 encoded image string

        Returns:
            Tuple of (image_bytes, format, (width, height))

        Raises:
            ValidationError: If any validation fails
        """
        image_bytes = ImageValidator.validate_base64_image(base64_data)
        image_format = ImageValidator.validate_image_format(image_bytes)
        dimensions = ImageValidator.validate_image_dimensions(image_bytes)

        logger.info(f"Image validation passed: {image_format}, {dimensions[0]}x{dimensions[1]}px, "
                    f"{len(image_bytes) / 1024:.1f}KB")

        return image_bytes, image_format, dimensions


class ErrorResponse:
    """Standardized error response formatter."""

    @staticmethod
    def format_error(error_code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format error response.

        Args:
            error_code: Machine-readable error code
            message: Human-readable error message
            details: Optional additional error details

        Returns:
            Formatted error dictionary
        """
        response = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message
            }
        }

        if details:
            response["error"]["details"] = details

        return response

    @staticmethod
    def log_error(error_type: str, message: str, **kwargs):
        """Log error with context."""
        logger.error(f"{error_type}: {message}", extra=kwargs)


class DatabaseErrorHandler:
    """Handles database-related errors gracefully."""

    @staticmethod
    def handle_connection_error(error: Exception, operation: str = "database operation") -> Dict[str, Any]:
        """
        Handle database connection errors.

        Args:
            error: The exception raised
            operation: Description of the operation that failed

        Returns:
            Formatted error response
        """
        logger.error(f"Database connection failed during {operation}: {str(error)}")
        return ErrorResponse.format_error(
            "DATABASE_CONNECTION_ERROR",
            f"Unable to complete {operation}. Please try again later.",
            {"error_type": str(type(error).__name__)}
        )

    @staticmethod
    def handle_query_error(error: Exception, query_type: str = "query") -> Dict[str, Any]:
        """
        Handle database query errors.

        Args:
            error: The exception raised
            query_type: Type of query that failed

        Returns:
            Formatted error response
        """
        logger.error(f"Database {query_type} failed: {str(error)}")
        return ErrorResponse.format_error(
            "DATABASE_QUERY_ERROR",
            f"Unable to execute {query_type}. Please try again.",
            {"error_type": str(type(error).__name__)}
        )


class LoggingSetup:
    """Configure structured logging for the application."""

    @staticmethod
    def setup_logging(log_file: str = "logs/app.log"):
        """
        Setup application logging.

        Args:
            log_file: Path to log file
        """
        import os
        from pathlib import Path

        # Create logs directory if needed
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure logging format
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(log_format)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        return root_logger
