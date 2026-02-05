from typing import Optional, Any


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
