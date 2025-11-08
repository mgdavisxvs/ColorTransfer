"""
Input Validation - Defense in Depth (Knuth/Graham)

Comprehensive input validation beyond Pydantic:
1. File size limits (prevent DoS, memory exhaustion)
2. Image format validation (magic numbers, not just extensions)
3. Content-based validation (actual image data verification)
4. Path traversal prevention
5. Malicious filename detection

Mathematical Analysis (Knuth):
- Size bounds: O(1) check, prevents O(n) memory attacks
- Format verification: O(1) magic number check
- Content validation: O(n) but bounded by size limits

Security Principles (Graham):
- Defense in depth: Multiple validation layers
- Fail securely: Default deny, explicit allow
- Clear error messages: Help legitimate users
- Performance: Fast checks before expensive operations
"""

import os
import re
import mimetypes
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Set
from enum import Enum

import numpy as np
import cv2


class ValidationSeverity(Enum):
    """Validation error severity"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """
    Result of validation check

    Knuth's Design:
    - Binary valid/invalid decision
    - Detailed error messages for debugging
    - Severity levels for different violations
    """
    valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class ValidationError(Exception):
    """Exception raised when validation fails"""

    def __init__(self, message: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.severity = severity
        super().__init__(message)


class FileValidator:
    """
    File Validation - Security First

    Knuth's Size Analysis:
    =====================

    Maximum file size prevents:
    1. Memory exhaustion: O(n) memory attack → O(1) rejection
    2. Disk exhaustion: Unbounded storage → Bounded storage
    3. Processing DoS: O(n²) operations on huge files

    Graham's Practical Limits:
    - 100 MB: Reasonable for high-res images
    - 10 MB: Good default for web uploads
    - 1 MB: Conservative for untrusted sources

    Path Traversal Prevention:
    - Block: ../, ..\, absolute paths
    - Allow: Relative paths within allowed directory
    """

    # Allowed file extensions (whitelist approach)
    ALLOWED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'
    }

    # Maximum file sizes (bytes)
    MAX_SIZE_DEFAULT = 100 * 1024 * 1024  # 100 MB
    MAX_SIZE_WEB = 10 * 1024 * 1024       # 10 MB
    MAX_SIZE_CONSERVATIVE = 1 * 1024 * 1024  # 1 MB

    # Dangerous filename patterns
    DANGEROUS_PATTERNS = [
        r'\.\.',           # Path traversal
        r'[<>:"|?*]',      # Invalid filename chars (Windows)
        r'^\.ht',          # Apache config files
        r'\.php$',         # Executable files
        r'\.exe$',
        r'\.sh$',
        r'\.bat$',
    ]

    def __init__(self, max_size: int = MAX_SIZE_DEFAULT):
        self.max_size = max_size

    def validate_file_size(self, file_path: str) -> ValidationResult:
        """
        Validate file size

        Security Analysis (Knuth):
        - Time complexity: O(1) - stat syscall
        - Prevents: Memory exhaustion, disk DoS
        - Fail fast: Check before reading file

        Mathematical Bound:
        - file_size <= max_size
        - If file_size > max_size: reject immediately
        """
        errors = []
        warnings = []

        try:
            file_size = os.path.getsize(file_path)

            if file_size > self.max_size:
                errors.append(
                    f"File size {file_size:,} bytes exceeds maximum "
                    f"{self.max_size:,} bytes"
                )

            # Warning for very small files (might be corrupted)
            if file_size < 100:
                warnings.append(
                    f"File size {file_size} bytes is unusually small"
                )

            metadata = {
                'file_size_bytes': file_size,
                'max_size_bytes': self.max_size,
                'size_utilization': file_size / self.max_size
            }

            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )

        except OSError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Cannot access file: {e}"],
                warnings=[]
            )

    def validate_filename(self, filename: str) -> ValidationResult:
        """
        Validate filename for security issues

        Graham's Security Checks:
        1. Path traversal: Block ../ and absolute paths
        2. Special characters: Block <, >, :, |, ?, *, etc.
        3. Executable extensions: Block .exe, .sh, .php, etc.
        4. Hidden files: Warn about files starting with .
        """
        errors = []
        warnings = []

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                errors.append(f"Filename contains dangerous pattern: {pattern}")

        # Check for path traversal
        if '..' in filename or os.path.isabs(filename):
            errors.append("Path traversal attempt detected")

        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            errors.append(
                f"Extension '{ext}' not allowed. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )

        # Warn about hidden files
        if filename.startswith('.'):
            warnings.append("Hidden file detected")

        # Check filename length (Unix: 255, Windows: 260 for path)
        if len(filename) > 255:
            errors.append(f"Filename too long: {len(filename)} > 255 characters")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Comprehensive file validation

        Validation Order (Graham):
        1. Filename check (fast, O(1))
        2. Size check (fast, O(1) stat)
        3. Existence check
        """
        all_errors = []
        all_warnings = []

        # Validate filename
        filename = os.path.basename(file_path)
        filename_result = self.validate_filename(filename)
        all_errors.extend(filename_result.errors)
        all_warnings.extend(filename_result.warnings)

        if not filename_result.valid:
            return ValidationResult(
                valid=False,
                errors=all_errors,
                warnings=all_warnings
            )

        # Check file exists
        if not os.path.exists(file_path):
            all_errors.append(f"File does not exist: {file_path}")
            return ValidationResult(
                valid=False,
                errors=all_errors,
                warnings=all_warnings
            )

        # Validate size
        size_result = self.validate_file_size(file_path)
        all_errors.extend(size_result.errors)
        all_warnings.extend(size_result.warnings)

        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            metadata=size_result.metadata
        )


class ImageValidator:
    """
    Image Content Validation - Beyond Extension Checking

    Knuth's Validation Hierarchy:
    ============================

    Level 1: Extension check - O(1), weak security
    Level 2: Magic number check - O(1), better security
    Level 3: Full parse - O(n), strongest security

    Magic Numbers (File Signatures):
    - PNG: 89 50 4E 47 0D 0A 1A 0A
    - JPEG: FF D8 FF
    - BMP: 42 4D
    - TIFF: 49 49 2A 00 (little-endian) or 4D 4D 00 2A (big-endian)
    - WebP: 52 49 46 46 ... 57 45 42 50

    Graham's Defense Strategy:
    1. Check magic numbers (fast, reliable)
    2. Attempt to parse with OpenCV (catches corrupted files)
    3. Validate image properties (dimensions, channels)
    """

    # Magic number signatures (first bytes of file)
    MAGIC_NUMBERS = {
        'png': bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),
        'jpeg': bytes([0xFF, 0xD8, 0xFF]),
        'bmp': bytes([0x42, 0x4D]),
        'tiff_le': bytes([0x49, 0x49, 0x2A, 0x00]),  # Little-endian
        'tiff_be': bytes([0x4D, 0x4D, 0x00, 0x2A]),  # Big-endian
        'webp': bytes([0x52, 0x49, 0x46, 0x46]),     # RIFF container
    }

    # Maximum reasonable image dimensions
    MAX_DIMENSION = 50000  # 50k pixels per dimension
    MAX_PIXELS = 100_000_000  # 100 megapixels

    def __init__(
        self,
        max_dimension: int = MAX_DIMENSION,
        max_pixels: int = MAX_PIXELS
    ):
        self.max_dimension = max_dimension
        self.max_pixels = max_pixels

    def validate_magic_number(self, file_path: str) -> ValidationResult:
        """
        Validate file format using magic numbers

        Knuth's Magic Number Analysis:
        - Read first N bytes (N <= 8 for image formats)
        - Compare against known signatures
        - More reliable than extension (user can change extension)

        Security Benefit:
        - Prevents extension spoofing: evil.exe renamed to evil.jpg
        - Fast: O(1) read of fixed bytes
        """
        errors = []
        warnings = []

        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # Read first 16 bytes

            # Check against known magic numbers
            detected_format = None

            if header.startswith(self.MAGIC_NUMBERS['png']):
                detected_format = 'png'
            elif header.startswith(self.MAGIC_NUMBERS['jpeg']):
                detected_format = 'jpeg'
            elif header.startswith(self.MAGIC_NUMBERS['bmp']):
                detected_format = 'bmp'
            elif header.startswith(self.MAGIC_NUMBERS['tiff_le']) or \
                 header.startswith(self.MAGIC_NUMBERS['tiff_be']):
                detected_format = 'tiff'
            elif header.startswith(self.MAGIC_NUMBERS['webp']) and b'WEBP' in header[:16]:
                detected_format = 'webp'
            else:
                errors.append(
                    f"Unknown or invalid image format. "
                    f"Header: {header[:8].hex()}"
                )

            # Check if extension matches detected format
            ext = Path(file_path).suffix.lower().lstrip('.')
            if detected_format and ext not in ['jpg', 'jpeg', 'png', 'bmp', 'tif', 'tiff', 'webp']:
                warnings.append(
                    f"Extension '.{ext}' doesn't match typical image extensions"
                )

            metadata = {
                'detected_format': detected_format,
                'file_extension': ext,
                'header_bytes': header[:8].hex()
            }

            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )

        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Error reading file header: {e}"],
                warnings=[]
            )

    def validate_image_content(self, file_path: str) -> ValidationResult:
        """
        Validate actual image content by parsing

        Graham's Parse Validation:
        1. Attempt to load with OpenCV
        2. Check image is not None (catches corrupted files)
        3. Validate dimensions and channels
        4. Check for reasonable properties

        Complexity: O(n) where n = file size
        Security: Catches corrupted/malicious files that pass magic number check
        """
        errors = []
        warnings = []

        try:
            # Attempt to read image
            img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)

            if img is None:
                errors.append("Failed to parse image file (corrupted or invalid format)")
                return ValidationResult(valid=False, errors=errors, warnings=[])

            # Validate dimensions
            height, width = img.shape[:2]

            if height > self.max_dimension or width > self.max_dimension:
                errors.append(
                    f"Image dimension {width}x{height} exceeds maximum "
                    f"{self.max_dimension}x{self.max_dimension}"
                )

            total_pixels = height * width
            if total_pixels > self.max_pixels:
                errors.append(
                    f"Image has {total_pixels:,} pixels, exceeds maximum "
                    f"{self.max_pixels:,} pixels"
                )

            # Validate channels
            if len(img.shape) == 2:
                channels = 1  # Grayscale
            else:
                channels = img.shape[2]

            if channels not in [1, 3, 4]:
                warnings.append(f"Unusual number of channels: {channels}")

            # Check for suspicious properties
            if height < 10 or width < 10:
                warnings.append(f"Unusually small image: {width}x{height}")

            if height == width and height in [1, 2, 4, 8, 16]:
                warnings.append(
                    f"Suspicious dimensions: {width}x{height} (might be generated)"
                )

            metadata = {
                'width': int(width),
                'height': int(height),
                'channels': int(channels),
                'total_pixels': int(total_pixels),
                'dtype': str(img.dtype),
                'size_bytes': img.nbytes
            }

            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )

        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Error validating image content: {e}"],
                warnings=[]
            )

    def validate_image(self, file_path: str) -> ValidationResult:
        """
        Complete image validation pipeline

        Validation Pipeline (Knuth):
        1. Magic number check - O(1), fast fail for non-images
        2. Content parse - O(n), thorough validation
        3. Property validation - O(1), dimension/channel checks

        This layered approach provides defense in depth.
        """
        all_errors = []
        all_warnings = []
        all_metadata = {}

        # Step 1: Magic number validation
        magic_result = self.validate_magic_number(file_path)
        all_errors.extend(magic_result.errors)
        all_warnings.extend(magic_result.warnings)
        all_metadata.update(magic_result.metadata or {})

        if not magic_result.valid:
            return ValidationResult(
                valid=False,
                errors=all_errors,
                warnings=all_warnings,
                metadata=all_metadata
            )

        # Step 2: Content validation
        content_result = self.validate_image_content(file_path)
        all_errors.extend(content_result.errors)
        all_warnings.extend(content_result.warnings)
        all_metadata.update(content_result.metadata or {})

        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            metadata=all_metadata
        )


class InputValidator:
    """
    Unified Input Validator

    Graham's Comprehensive Validation:
    - Combines file and image validation
    - Single interface for all input checks
    - Detailed error reporting

    Usage:
        validator = InputValidator(max_file_size=10*1024*1024)  # 10 MB

        result = validator.validate("/path/to/image.jpg")

        if not result.valid:
            raise ValidationError("; ".join(result.errors))
    """

    def __init__(
        self,
        max_file_size: int = FileValidator.MAX_SIZE_DEFAULT,
        max_dimension: int = ImageValidator.MAX_DIMENSION,
        max_pixels: int = ImageValidator.MAX_PIXELS
    ):
        self.file_validator = FileValidator(max_file_size)
        self.image_validator = ImageValidator(max_dimension, max_pixels)

    def validate(self, file_path: str, check_content: bool = True) -> ValidationResult:
        """
        Complete input validation

        Args:
            file_path: Path to file to validate
            check_content: If True, parse and validate image content (slower)

        Returns:
            ValidationResult with all errors, warnings, and metadata

        Knuth's Validation Order:
        1. File validation (fast)
        2. Image validation (slower, optional)

        This ordering minimizes wasted computation on invalid files.
        """
        all_errors = []
        all_warnings = []
        all_metadata = {}

        # File validation
        file_result = self.file_validator.validate_file(file_path)
        all_errors.extend(file_result.errors)
        all_warnings.extend(file_result.warnings)
        all_metadata.update(file_result.metadata or {})

        if not file_result.valid:
            return ValidationResult(
                valid=False,
                errors=all_errors,
                warnings=all_warnings,
                metadata=all_metadata
            )

        # Image validation (if requested)
        if check_content:
            image_result = self.image_validator.validate_image(file_path)
            all_errors.extend(image_result.errors)
            all_warnings.extend(image_result.warnings)
            all_metadata.update(image_result.metadata or {})

        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            metadata=all_metadata
        )


# Knuth's Security Analysis Summary
"""
Input Validation Security Analysis (Knuth/Graham):
==================================================

Attack Prevention:
1. Memory Exhaustion: File size limits prevent O(n) memory attacks
2. Path Traversal: Filename validation blocks directory traversal
3. Extension Spoofing: Magic numbers prevent evil.exe → evil.jpg
4. Malformed Input: Content parsing catches corrupted/malicious files
5. Processing DoS: Dimension limits prevent O(n²) processing attacks

Performance:
- File validation: O(1) - stat + regex checks
- Magic number: O(1) - read fixed bytes
- Content parse: O(n) - but bounded by size limit
- Total: O(n) where n <= max_file_size

False Positive Rate:
- Very low: Legitimate images pass all checks
- Magic numbers are reliable (standardized)
- OpenCV parsing is robust

False Negative Rate:
- Low: Multi-layer validation catches most attacks
- Content parsing prevents header-only spoofing
- Dimension checks prevent processing bombs

Graham's Recommendation:
- Always validate file size first (fast, prevents DoS)
- Use magic numbers, not extensions (security)
- Parse content for untrusted sources (thorough)
- Balance security vs performance based on threat model
"""
