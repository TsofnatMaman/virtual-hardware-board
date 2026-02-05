import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from simulator.core.exceptions import ConfigurationError
from simulator.utils.config_loader import (
    GPIO_Config,
    GPIO_Offsets,
    Memory_Config,
    NVIC_Config,
    Pins_Config,
    Simulator_Config,
    SysCtl_Config,
    Util_Config,
    _ensure_yaml_available,
    _get_config_path,
    _load_yaml_file,
    _parse_simulator_cfg_from_dict,
    get_config,
    load_config,
)


class TestMemoryConfig:
    """Test Memory_Config dataclass."""

    def test_memory_config_creation(self):
        """Test creating Memory_Config with valid values."""
        cfg = Memory_Config(
            flash_base=0x08000000,
            flash_size=524288,
            sram_base=0x20000000,
            sram_size=131072,
            periph_base=0x40000000,
            periph_size=0x00100000,
            bitband_base=0x42000000,
            bitband_size=0x02000000,
        )

        assert cfg.flash_base == 0x08000000
        assert cfg.flash_size == 524288
        assert cfg.sram_base == 0x20000000
        assert cfg.sram_size == 131072
        assert cfg.periph_base == 0x40000000
        assert cfg.periph_size == 0x00100000
        assert cfg.bitband_base == 0x42000000
        assert cfg.bitband_size == 0x02000000

    def test_memory_config_immutable(self):
        """Test that Memory_Config is frozen."""
        cfg = Memory_Config(
            flash_base=0x08000000,
            flash_size=524288,
            sram_base=0x20000000,
            sram_size=131072,
            periph_base=0x40000000,
            periph_size=0x00100000,
            bitband_base=0x42000000,
            bitband_size=0x02000000,
        )

        with pytest.raises(AttributeError):
            cfg.flash_base = 0x0


class TestUtilConfig:
    """Test Util_Config dataclass."""

    def test_util_config_creation(self):
        """Test creating Util_Config with valid values."""
        cfg = Util_Config(mask_32bit=0xFFFFFFFF, mask_8bit=0xFF)

        assert cfg.mask_32bit == 0xFFFFFFFF
        assert cfg.mask_8bit == 0xFF

    def test_util_config_immutable(self):
        """Test that Util_Config is frozen."""
        cfg = Util_Config(mask_32bit=0xFFFFFFFF, mask_8bit=0xFF)

        with pytest.raises(AttributeError):
            cfg.mask_32bit = 0x00


class TestGPIOOffsets:
    """Test GPIO_Offsets dataclass."""

    def test_gpio_offsets_creation(self):
        """Test creating GPIO_Offsets with valid values."""
        offsets = GPIO_Offsets(
            data=0x000,
            dir=0x400,
            den=0x51C,
            lock=0x520,
            cr=0x524,
            icr=0x41C,
        )

        assert offsets.data == 0x000
        assert offsets.dir == 0x400
        assert offsets.den == 0x51C
        assert offsets.lock == 0x520
        assert offsets.cr == 0x524
        assert offsets.icr == 0x41C

    def test_gpio_offsets_immutable(self):
        """Test that GPIO_Offsets is frozen."""
        offsets = GPIO_Offsets(
            data=0x000,
            dir=0x400,
            den=0x51C,
            lock=0x520,
            cr=0x524,
            icr=0x41C,
        )

        with pytest.raises(AttributeError):
            offsets.data = 0x100


class TestGPIOConfig:
    """Test GPIO_Config dataclass."""

    def test_gpio_config_creation(self):
        """Test creating GPIO_Config with valid values."""
        offsets = GPIO_Offsets(
            data=0x000,
            dir=0x400,
            den=0x51C,
            lock=0x520,
            cr=0x524,
            icr=0x41C,
        )
        ports = {
            "A": 0x40004000,
            "B": 0x40005000,
        }

        cfg = GPIO_Config(ports=ports, offsets=offsets)

        assert cfg.ports == ports
        assert cfg.offsets == offsets


class TestSysCtlConfig:
    """Test SysCtl_Config dataclass."""

    def test_sysctl_config_creation(self):
        """Test creating SysCtl_Config with valid values."""
        registers = {
            "rcgcgpio": 0x608,
            "rcgctimer": 0x604,
        }
        cfg = SysCtl_Config(base=0x400FE000, registers=registers)

        assert cfg.base == 0x400FE000
        assert cfg.registers == registers


class TestPinsConfig:
    """Test Pins_Config dataclass."""

    def test_pins_config_creation(self):
        """Test creating Pins_Config with valid values."""
        pin_masks = {"PIN0": 0x01, "PIN1": 0x02}
        leds = {"LED1": 0x01}

        cfg = Pins_Config(pin_masks=pin_masks, leds=leds)

        assert cfg.pin_masks == pin_masks
        assert cfg.leds == leds


class TestNVICConfig:
    """Test NVIC_Config dataclass."""

    def test_nvic_config_creation(self):
        """Test creating NVIC_Config with valid values."""
        irq = {"timer": 19, "gpio": 0}
        cfg = NVIC_Config(irq=irq, irq_offset=16)

        assert cfg.irq == irq
        assert cfg.irq_offset == 16

    def test_nvic_config_empty_irq(self):
        """Test creating NVIC_Config with empty IRQ map."""
        cfg = NVIC_Config(irq={}, irq_offset=16)

        assert cfg.irq == {}
        assert cfg.irq_offset == 16


class TestEnsureYamlAvailable:
    """Test _ensure_yaml_available function."""

    def test_yaml_available(self):
        """Test when PyYAML is available."""
        # This should not raise
        _ensure_yaml_available()

    def test_yaml_not_available(self):
        """Test when PyYAML is not available."""
        with patch("simulator.utils.config_loader.yaml", None):
            with pytest.raises(ConfigurationError) as exc_info:
                _ensure_yaml_available()

            assert "PyYAML is required" in str(exc_info.value)


class TestGetConfigPath:
    """Test _get_config_path function."""

    def test_get_config_path_default(self):
        """Test getting config path with default location."""
        path = _get_config_path("tm4c123")

        assert "tm4c123" in path
        assert "config.yaml" in path

    def test_get_config_path_custom(self):
        """Test getting config path with custom location."""
        custom_path = "/path/to/custom/config.yaml"
        path = _get_config_path("tm4c123", custom_path)

        assert path == custom_path


class TestLoadYamlFile:
    """Test _load_yaml_file function."""

    def test_load_valid_yaml(self):
        """Test loading a valid YAML file."""
        yaml_content = {
            "memory": {"flash_base": 0x08000000},
            "util": {"mask_32bit": 0xFFFFFFFF},
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
        ) as f:
            yaml.dump(yaml_content, f)
            f.flush()
            path = Path(f.name)

        try:
            result = _load_yaml_file(path)
            assert result == yaml_content
        finally:
            path.unlink()

    def test_load_invalid_yaml(self):
        """Test loading an invalid YAML file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
        ) as f:
            f.write("{ invalid: yaml: content")
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                _load_yaml_file(path)

            assert "Failed to parse config" in str(exc_info.value)
        finally:
            path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file."""
        path = Path("/nonexistent/path/config.yaml")

        with pytest.raises(ConfigurationError) as exc_info:
            _load_yaml_file(path)

        assert "Failed to parse config" in str(exc_info.value)


class TestParseSimulatorCfgFromDict:
    """Test _parse_simulator_cfg_from_dict function."""

    @pytest.fixture
    def valid_config_dict(self):
        """Fixture providing a valid configuration dictionary."""
        return {
            "memory": {
                "flash_base": 0x08000000,
                "flash_size": 524288,
                "sram_base": 0x20000000,
                "sram_size": 131072,
                "periph_base": 0x40000000,
                "periph_size": 0x00100000,
                "bitband_base": 0x42000000,
                "bitband_size": 0x02000000,
            },
            "util": {
                "mask_32bit": 0xFFFFFFFF,
                "mask_8bit": 0xFF,
            },
            "gpio": {
                "ports": {"A": 0x40004000, "B": 0x40005000},
                "offsets": {
                    "data": 0x000,
                    "dir": 0x400,
                    "den": 0x51C,
                    "lock": 0x520,
                    "cr": 0x524,
                    "icr": 0x41C,
                },
            },
            "sysctl": {
                "base": 0x400FE000,
                "registers": {
                    "rcgcgpio": 0x608,
                    "rcgctimer": 0x604,
                },
            },
            "pins": {
                "pin_masks": {"PIN0": 0x01, "PIN1": 0x02},
                "leds": {"LED1": 0x01},
                "switches": {"SW1": 0x01},
            },
            "nvic": {
                "irq": {"timer": 19},
                "irq_offset": 16,
            },
        }

    def test_parse_valid_config(self, valid_config_dict):
        """Test parsing a valid configuration dictionary."""
        cfg = _parse_simulator_cfg_from_dict(valid_config_dict)

        assert isinstance(cfg, Simulator_Config)
        assert cfg.memory.flash_base == 0x08000000
        assert cfg.util.mask_32bit == 0xFFFFFFFF
        assert cfg.gpio.ports["A"] == 0x40004000
        assert cfg.sysctl.base == 0x400FE000
        assert cfg.pins.leds["LED1"] == 0x01
        assert cfg.nvic.irq["timer"] == 19

    def test_parse_missing_memory_section(self, valid_config_dict):
        """Test parsing with missing memory section."""
        del valid_config_dict["memory"]

        with pytest.raises(ConfigurationError) as exc_info:
            _parse_simulator_cfg_from_dict(valid_config_dict)

        assert "Missing required config key" in str(exc_info.value)

    def test_parse_missing_util_section(self, valid_config_dict):
        """Test parsing with missing util section."""
        del valid_config_dict["util"]

        with pytest.raises(ConfigurationError) as exc_info:
            _parse_simulator_cfg_from_dict(valid_config_dict)

        assert "Missing required config key" in str(exc_info.value)

    def test_parse_missing_gpio_section(self, valid_config_dict):
        """Test parsing with missing gpio section."""
        del valid_config_dict["gpio"]

        with pytest.raises(ConfigurationError) as exc_info:
            _parse_simulator_cfg_from_dict(valid_config_dict)

        assert "Missing required config key" in str(exc_info.value)

    def test_parse_missing_sysctl_section(self, valid_config_dict):
        """Test parsing with missing sysctl section."""
        del valid_config_dict["sysctl"]

        with pytest.raises(ConfigurationError) as exc_info:
            _parse_simulator_cfg_from_dict(valid_config_dict)

        assert "Missing required config key" in str(exc_info.value)

    def test_parse_missing_pins_section(self, valid_config_dict):
        """Test parsing with missing pins section."""
        del valid_config_dict["pins"]

        with pytest.raises(ConfigurationError) as exc_info:
            _parse_simulator_cfg_from_dict(valid_config_dict)

        assert "Missing required config key" in str(exc_info.value)

    def test_parse_optional_nvic_section(self, valid_config_dict):
        """Test parsing with missing optional nvic section."""
        del valid_config_dict["nvic"]

        cfg = _parse_simulator_cfg_from_dict(valid_config_dict)

        assert cfg.nvic.irq == {}
        assert cfg.nvic.irq_offset == 16

    def test_parse_invalid_gpio_offsets(self, valid_config_dict):
        """Test parsing with missing gpio offset."""
        del valid_config_dict["gpio"]["offsets"]["data"]

        with pytest.raises(ConfigurationError) as exc_info:
            _parse_simulator_cfg_from_dict(valid_config_dict)

        assert "Invalid config schema" in str(exc_info.value)

    def test_parse_invalid_sysctl_base_type(self, valid_config_dict):
        """Test parsing with invalid sysctl base type."""
        valid_config_dict["sysctl"]["base"] = []

        with pytest.raises(ConfigurationError) as exc_info:
            _parse_simulator_cfg_from_dict(valid_config_dict)

        assert "Invalid config schema" in str(exc_info.value)


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_success(self):
        """Test successfully loading configuration."""
        yaml_content = {
            "memory": {
                "flash_base": 0x08000000,
                "flash_size": 524288,
                "sram_base": 0x20000000,
                "sram_size": 131072,
                "periph_base": 0x40000000,
                "periph_size": 0x00100000,
                "bitband_base": 0x42000000,
                "bitband_size": 0x02000000,
            },
            "util": {
                "mask_32bit": 0xFFFFFFFF,
                "mask_8bit": 0xFF,
            },
            "gpio": {
                "ports": {"A": 0x40004000},
                "offsets": {
                    "data": 0x000,
                    "dir": 0x400,
                    "den": 0x51C,
                    "lock": 0x520,
                    "cr": 0x524,
                    "icr": 0x41C,
                },
            },
            "sysctl": {
                "base": 0x400FE000,
                "registers": {"rcgcgpio": 0x608},
            },
            "pins": {
                "pin_masks": {"PIN0": 0x01},
                "leds": {"LED1": 0x01},
                "switches": {"SW1": 0x01},
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
        ) as f:
            yaml.dump(yaml_content, f)
            f.flush()
            path = f.name

        try:
            cfg = load_config("test_board", path=path)

            assert isinstance(cfg, Simulator_Config)
            assert cfg.memory.flash_base == 0x08000000
            assert cfg.util.mask_32bit == 0xFFFFFFFF
        finally:
            Path(path).unlink()

    def test_load_config_invalid_path(self):
        """Test loading configuration from invalid path."""
        with pytest.raises(ConfigurationError) as exc_info:
            load_config("test_board", path="/nonexistent/path/config.yaml")

        assert "Failed to parse config" in str(exc_info.value)

    def test_load_config_malformed_yaml(self):
        """Test loading malformed YAML."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
        ) as f:
            f.write("{ invalid: yaml")
            f.flush()
            path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_config("test_board", path=path)

            assert "Failed to parse config" in str(exc_info.value)
        finally:
            Path(path).unlink()


class TestGetConfig:
    """Test get_config function."""

    def test_get_config_docstring(self):
        """Test that get_config has proper documentation."""
        assert get_config.__doc__ is not None
        assert (
            "load the config" in get_config.__doc__.lower()
            or "return" in get_config.__doc__.lower()
        )

    def test_get_config_loads_default_when_none(self):
        """Load default config when cache is empty."""
        with patch(
            "simulator.utils.config_loader._LOADER_CONFIG",
            None,
        ):
            with patch(
                "simulator.utils.config_loader.load_config"
            ) as mock_load:
                mock_config = Mock(spec=Simulator_Config)
                mock_load.return_value = mock_config

                result = get_config("tm4c123")

                mock_load.assert_called_once_with(board_name="tm4c123")
                assert result == mock_config

    def test_get_config_returns_cached_config(
        self, valid_simulator_config_dict
    ):
        """Return cached config when available."""
        mock_config = _parse_simulator_cfg_from_dict(
            valid_simulator_config_dict
        )

        with patch(
            "simulator.utils.config_loader._LOADER_CONFIG",
            mock_config,
        ):
            with patch(
                "simulator.utils.config_loader.load_config"
            ) as mock_load:
                result = get_config("tm4c123")

                # load_config should not be called
                mock_load.assert_not_called()
                assert result == mock_config

    def test_get_config_uses_board_name_parameter(self):
        """Pass board_name argument to load_config."""
        with patch(
            "simulator.utils.config_loader._LOADER_CONFIG",
            None,
        ):
            with patch(
                "simulator.utils.config_loader.load_config"
            ) as mock_load:
                mock_config = Mock(spec=Simulator_Config)
                mock_load.return_value = mock_config

                get_config("custom_board")

                mock_load.assert_called_once_with(board_name="custom_board")
