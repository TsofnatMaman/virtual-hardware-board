import pytest

from simulator.core.exceptions import SimulatorError, ConfigurationError


class TestSimulatorError:
    """Test SimulatorError base exception class."""

    def test_simulator_error_creation_basic(self):
        """Test creating a SimulatorError with just a message."""
        msg = "Test error message"
        exc = SimulatorError(msg)

        assert str(exc) == msg
        assert exc.details == {}

    def test_simulator_error_with_details(self):
        """Test creating a SimulatorError with details."""
        msg = "Test error message"
        details = {"key1": "value1", "key2": 42}
        exc = SimulatorError(msg, details=details)

        assert str(exc) == msg
        assert exc.details == details

    def test_simulator_error_empty_details(self):
        """Test creating a SimulatorError with empty details dict."""
        msg = "Test error"
        exc = SimulatorError(msg, details={})

        assert exc.details == {}

    def test_simulator_error_inheritance(self):
        """Test that SimulatorError inherits from Exception."""
        exc = SimulatorError("test")

        assert isinstance(exc, Exception)

    def test_simulator_error_with_complex_details(self):
        """Test SimulatorError with complex nested details."""
        msg = "Complex error"
        details = {
            "nested": {"level1": {"level2": "value"}},
            "list": [1, 2, 3],
            "config": {"setting": "enabled"},
        }
        exc = SimulatorError(msg, details=details)

        assert exc.details == details
        assert exc.details["nested"]["level1"]["level2"] == "value"

    def test_simulator_error_none_details_defaults_to_empty(self):
        """Test that None details defaults to empty dict."""
        exc = SimulatorError("message", details=None)

        assert exc.details == {}


class TestConfigurationError:
    """Test ConfigurationError exception class."""

    def test_configuration_error_with_message_only(self):
        """Test ConfigurationError with only a message (treated as config_key)."""
        exc = ConfigurationError(config_key="Missing config key")

        assert "configuration" in str(exc).lower()
        assert "Missing config key" in str(exc)

    def test_configuration_error_with_key_and_message(self):
        """Test ConfigurationError with both key and message."""
        exc = ConfigurationError(
            config_key="database_url", message="URL must not be empty"
        )

        assert "database_url" in str(exc)
        assert "URL must not be empty" in str(exc)

    def test_configuration_error_with_details(self):
        """Test ConfigurationError with details."""
        exc = ConfigurationError(
            config_key="port",
            message="Invalid port number",
            details={"provided": 99999, "max": 65535},
        )

        assert "port" in str(exc)
        assert "Invalid port number" in str(exc)
        assert exc.details == {"provided": 99999, "max": 65535}

    def test_configuration_error_none_key_defaults(self):
        """Test ConfigurationError with None key."""
        exc = ConfigurationError(config_key=None, message="Something is wrong")

        assert "configuration" in str(exc).lower()
        assert "Something is wrong" in str(exc)

    def test_configuration_error_message_none_uses_key_as_message(self):
        """Test ConfigurationError where message is None uses key as message."""
        exc = ConfigurationError(config_key="api_key")

        assert "api_key" in str(exc)
        assert "configuration" in str(exc).lower()

    def test_configuration_error_inheritance(self):
        """Test that ConfigurationError inherits from SimulatorError."""
        exc = ConfigurationError(config_key="test")

        assert isinstance(exc, SimulatorError)
        assert isinstance(exc, Exception)

    def test_configuration_error_no_args(self):
        """Test ConfigurationError with no arguments."""
        exc = ConfigurationError()

        assert "Invalid configuration" in str(exc)
        assert exc.details == {}

    def test_configuration_error_multiple_details(self):
        """Test ConfigurationError with multiple detail entries."""
        details = {
            "key": "memory.flash_size",
            "expected_type": "int",
            "actual_type": "str",
            "value": "524288",
        }
        exc = ConfigurationError(
            config_key="type_mismatch",
            message="Type validation failed",
            details=details,
        )

        assert exc.details == details
        assert exc.details["key"] == "memory.flash_size"

    def test_configuration_error_none_details_defaults_to_empty(self):
        """Test that None details defaults to empty dict."""
        exc = ConfigurationError(config_key="test", message="test error", details=None)

        assert exc.details == {}


class TestExceptionBehavior:
    """Test exception behavior and raise/catch patterns."""

    def test_catch_simulator_error_catches_all_simulator_exceptions(self):
        """Test that catching SimulatorError catches ConfigurationError."""
        with pytest.raises(SimulatorError):
            raise ConfigurationError(config_key="test")

    def test_catch_configuration_error_does_not_catch_all(self):
        """Test that catching ConfigurationError does not catch base SimulatorError."""
        with pytest.raises(SimulatorError):
            with pytest.raises(ConfigurationError):
                raise SimulatorError("test")

    def test_exception_string_representation(self):
        """Test string representation of exceptions."""
        exc = ConfigurationError(
            config_key="timeout", message="Timeout value must be positive"
        )
        exc_str = str(exc)

        assert len(exc_str) > 0
        assert isinstance(exc_str, str)

    def test_raise_and_catch_with_context(self):
        """Test raising exception with context."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise SimulatorError("Wrapped error") from e
        except SimulatorError as e:
            assert "Wrapped error" == str(e)
            assert isinstance(e.__cause__, ValueError)

    def test_exception_info_preservation(self):
        """Test that exception info is preserved through raise."""
        obj = ConfigurationError(
            config_key="key", message="msg", details={"info": "preserved"}
        )

        try:
            raise obj
        except ConfigurationError as e:
            assert e.details == {"info": "preserved"}


class TestSimulatorErrorEdgeCases:
    """Test edge cases for SimulatorError."""

    def test_error_with_unicode_characters(self):
        """Test error with unicode characters."""
        msg = "Error with unicode: αβγδε 中文 العربية"
        exc = SimulatorError(msg)

        assert msg in str(exc)

    def test_error_with_special_characters(self):
        """Test error with special characters."""
        msg = "Error with special chars: !@#$%^&*()_+-=[]{}|;:,.<>?"
        exc = SimulatorError(msg)

        assert msg in str(exc)

    def test_error_with_empty_message(self):
        """Test SimulatorError with empty message."""
        exc = SimulatorError("")

        assert str(exc) == ""

    def test_error_with_very_long_message(self):
        """Test SimulatorError with very long message."""
        msg = "A" * 10000
        exc = SimulatorError(msg)

        assert str(exc) == msg
        assert len(str(exc)) == 10000


class TestConfigurationErrorEdgeCases:
    """Test edge cases for ConfigurationError."""

    def test_configuration_error_with_empty_key(self):
        """Test ConfigurationError with empty string key."""
        exc = ConfigurationError(config_key="", message="error")

        # Even with empty key, config_key is still set
        assert "error" in str(exc)

    def test_configuration_error_with_empty_message(self):
        """Test ConfigurationError with empty string message."""
        exc = ConfigurationError(config_key="key", message="")

        assert "key" in str(exc)

    def test_configuration_error_details_with_none_values(self):
        """Test ConfigurationError details containing None values."""
        details = {"value1": None, "value2": "present", "value3": None}
        exc = ConfigurationError(config_key="test", details=details)

        assert exc.details["value1"] is None
        assert exc.details["value2"] == "present"
