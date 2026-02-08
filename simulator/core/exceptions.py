"""Custom exceptions used throughout the simulator package."""

from typing import Any, Optional


class SimulatorError(Exception):
    """Base exception for all simulator errors.

    All simulator-specific exceptions should inherit from this class.
    This allows catching all simulator errors with a single except clause.
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional context about the error
        """

        super().__init__(message)
        self.details = details or {}


class ConfigurationError(SimulatorError):
    """Raised when there's an error in configuration.

    This includes:
    - Invalid configuration value
    - Missing required configuration
    - Configuration validation failures
    """

    def __init__(
        self,
        config_key: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize configuration error.

        Args:
            config_key: The configuration key that caused the error
            message: Description of what's wrong. If omitted, config_key is
                treated as the message and the key defaults to "configuration".
            details: Additional context
        """
        if message is None:
            message = config_key or "Invalid configuration"
            config_key = "configuration"
        if config_key is None:
            config_key = "configuration"

        full_message = f"Configuration error for '{config_key}': {message}"
        super().__init__(message=full_message, details=details)
        self.config_key = config_key


class MemoryException(SimulatorError):
    """Base exception for all memory-related errors.

    Raised for invalid memory accesses, permissions, or memory map violations.
    """

    def __init__(
        self,
        message: str,
        address: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if address is not None:
            details = details or {}
            details["address"] = f"0x{address:08X}"

        super().__init__(message=message, details=details)
        self.address = address


class MemoryAccessError(MemoryException):
    """Raised when accessing an invalid or unmapped memory address.

    Examples:
    - Address not mapped to any memory region
    - Peripheral not found at address
    """

    def __init__(
        self,
        address: int,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if message is None:
            message = f"Invalid memory access at 0x{address:08X}"
        super().__init__(message=message, address=address, details=details)


class MemoryPermissionError(MemoryException):
    """Raised when attempting an operation not allowed on a memory region.

    Examples:
    - Writing to FLASH
    - Executing from non-executable region (future)
    """

    def __init__(
        self,
        address: int,
        operation: str,
        details: Optional[dict[str, Any]] = None,
    ):
        message = f"Memory permission error: cannot {operation} at 0x{address:08X}"
        super().__init__(message=message, address=address, details=details)
        self.operation = operation


class MemoryAlignmentError(MemoryException):
    """Raised when a memory access is not properly aligned.

    Examples:
    - 4-byte read on non-4-byte-aligned address
    """

    def __init__(
        self,
        address: int,
        size: int,
        details: Optional[dict[str, Any]] = None,
    ):
        message = (
            f"Unaligned memory access at 0x{address:08X} "
            f"for access size {size} bytes"
        )
        super().__init__(message=message, address=address, details=details)
        self.size = size


class MemoryBoundsError(MemoryException):
    """Raised when a memory access exceeds the bounds of a region.

    Examples:
    - offset + size exceeds SRAM or FLASH size
    """

    def __init__(
        self,
        address: int,
        size: int,
        region: str,
        details: Optional[dict[str, Any]] = None,
    ):
        message = (
            f"Out-of-bounds access in {region}: "
            f"address=0x{address:08X}, size={size}"
        )
        super().__init__(message=message, address=address, details=details)
        self.size = size
        self.region = region
