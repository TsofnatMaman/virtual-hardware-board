import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from simulator.core.exceptions import ConfigurationError
from simulator.utils.config_loader import (
    MemoryConfig,
    Tm4cGpioOffsets,
    Stm32GpioOffsets,
    Tm4cGpioConfig,
    Stm32GpioConfig,
    SimulatorConfig,
    _get_config_path,
    _load_yaml_file,
    _parse_simulator_cfg_from_dict,
    get_config,
    load_config,
)


class TestMemoryConfig:
    def test_memory_config_creation(self):
        cfg = MemoryConfig(
            flash_base=0x08000000,
            flash_size=524288,
            sram_base=0x20000000,
            sram_size=131072,
            periph_base=0x40000000,
            periph_size=0x00100000,
            bitband_sram_base=0x22000000,
            bitband_sram_size=0x02000000,
            bitband_periph_base=0x42000000,
            bitband_periph_size=0x02000000,
        )
        assert cfg.flash_base == 0x08000000
        assert cfg.bitband_sram_base == 0x22000000

    def test_memory_config_immutable(self):
        cfg = MemoryConfig(
            flash_base=0x08000000,
            flash_size=524288,
            sram_base=0x20000000,
            sram_size=131072,
            periph_base=0x40000000,
            periph_size=0x00100000,
            bitband_sram_base=0x22000000,
            bitband_sram_size=0x02000000,
            bitband_periph_base=0x42000000,
            bitband_periph_size=0x02000000,
        )
        with pytest.raises(AttributeError):
            cfg.flash_base = 0


class TestGpioOffsets:
    def test_tm4c_offsets(self):
        offsets = Tm4cGpioOffsets(
            data=0x000,
            dir=0x400,
            den=0x51C,
            lock=0x520,
            cr=0x524,
            is_=0x404,
            ibe=0x408,
            iev=0x40C,
            im=0x410,
            ris=0x414,
            mis=0x418,
            icr=0x41C,
            afsel=0x420,
        )
        assert offsets.data == 0x000

    def test_stm32_offsets(self):
        offsets = Stm32GpioOffsets(idr=0x10, odr=0x14, bsrr=0x18)
        assert offsets.idr == 0x10


class TestGetConfigPath:
    def test_get_config_path_default(self):
        path = _get_config_path("tm4c123")
        assert "tm4c123" in path
        assert "config.yaml" in path

    def test_get_config_path_custom(self):
        custom_path = "/path/to/custom/config.yaml"
        path = _get_config_path("tm4c123", custom_path)
        assert path == custom_path


class TestLoadYamlFile:
    def test_load_valid_yaml(self):
        yaml_content = {"memory": {"flash_base": 0x08000000}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            f.flush()
            path = Path(f.name)
        try:
            result = _load_yaml_file(path)
            assert result == yaml_content
        finally:
            path.unlink()

    def test_load_invalid_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("{ invalid: yaml: content")
            f.flush()
            path = Path(f.name)
        try:
            with pytest.raises(ConfigurationError):
                _load_yaml_file(path)
        finally:
            path.unlink()


class TestParseSimulatorCfgFromDict:
    @pytest.fixture
    def valid_config_dict(self):
        return {
            "memory": {
                "flash_base": 0x08000000,
                "flash_size": 524288,
                "sram_base": 0x20000000,
                "sram_size": 131072,
                "periph_base": 0x40000000,
                "periph_size": 0x00100000,
                "bitband_sram_base": 0x22000000,
                "bitband_sram_size": 0x02000000,
                "bitband_periph_base": 0x42000000,
                "bitband_periph_size": 0x02000000,
            },
            "gpio": {
                "kind": "tm4c123",
                "port_size": 0x1000,
                "ports": {"A": 0x40004000, "B": 0x40005000},
                "offsets": {
                    "data": 0x000,
                    "dir": 0x400,
                    "den": 0x51C,
                    "lock": 0x520,
                    "cr": 0x524,
                    "is": 0x404,
                    "ibe": 0x408,
                    "iev": 0x40C,
                    "im": 0x410,
                    "ris": 0x414,
                    "mis": 0x418,
                    "icr": 0x41C,
                    "afsel": 0x420,
                },
            },
            "sysctl": {"base": 0x400FE000, "registers": {"rcgcgpio": 0x608}},
            "pins": {"pin_masks": {"PIN0": 0x01}, "leds": {"LED1": 0x01}},
            "nvic": {"irq": {"timer": 19}, "irq_offset": 16},
        }

    def test_parse_valid_config(self, valid_config_dict):
        cfg = _parse_simulator_cfg_from_dict(valid_config_dict)
        assert isinstance(cfg, SimulatorConfig)
        assert isinstance(cfg.gpio, Tm4cGpioConfig)
        assert cfg.gpio.kind == "tm4c123"

    def test_parse_invalid_gpio_kind(self, valid_config_dict):
        valid_config_dict["gpio"]["kind"] = "unknown"
        with pytest.raises(ConfigurationError):
            _parse_simulator_cfg_from_dict(valid_config_dict)


class TestLoadConfig:
    def test_load_config_success(self, temp_yaml_file, minimal_simulator_config_dict):
        with temp_yaml_file.open("w", encoding="utf-8") as fh:
            yaml.dump(minimal_simulator_config_dict, fh)
        cfg = load_config("test_board", path=str(temp_yaml_file))
        assert isinstance(cfg, SimulatorConfig)


class TestGetConfig:
    def test_get_config_loads_default_when_none(self):
        with patch("simulator.utils.config_loader._LOADER_CACHE", {}):
            with patch("simulator.utils.config_loader.load_config") as mock_load:
                mock_config = Mock(spec=SimulatorConfig)
                mock_load.return_value = mock_config
                result = get_config("tm4c123")
                mock_load.assert_called_once_with(board_name="tm4c123")
                assert result == mock_config
