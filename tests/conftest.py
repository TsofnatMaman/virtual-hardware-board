"""
Pytest configuration and shared fixtures for the simulator test suite.
"""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Ensure project root is on PYTHONPATH so 'simulator' can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_yaml_file():
    """
    Fixture that provides a temporary YAML file.

    Yields:
        Path: Path to the temporary YAML file
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        delete=False,
    ) as f:
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


MEMORY_CFG = {
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
}

GPIO_PORTS = {
    "A": 0x40004000,
    "B": 0x40005000,
    "C": 0x40006000,
    "D": 0x40007000,
    "E": 0x40024000,
    "F": 0x40025000,
}

GPIO_OFFSETS = {
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
}

SYSCTL_CFG = {
    "base": 0x400FE000,
    "registers": {
        "rcgcgpio": 0x608,
        "rcgctimer": 0x604,
        "rcgcuart": 0x618,
        "rcgcssi": 0x61C,
        "rcgci2c": 0x620,
        "rcgcpwm": 0x640,
        "rcgcadc": 0x638,
    },
}

PIN_MASKS = {
    "PIN0": 0x01,
    "PIN1": 0x02,
    "PIN2": 0x04,
    "PIN3": 0x08,
    "PIN4": 0x10,
    "PIN5": 0x20,
    "PIN6": 0x40,
}

PINS_CFG = {
    "pin_masks": PIN_MASKS,
    "leds": {"LED1": 0x01, "LED2": 0x02},
    "switches": {"SW1": 0x01, "SW2": 0x02},
}

NVIC_CFG = {"irq": {"timer": 19, "gpio": 0}, "irq_offset": 16}

# STM32 Configuration
STM32_GPIO_PORTS = {
    "A": 0x40020000,
    "B": 0x40020400,
    "C": 0x40020800,
    "D": 0x40020C00,
    "E": 0x40021000,
    "F": 0x40021400,
    "G": 0x40021800,
}

STM32_GPIO_OFFSETS = {
    "idr": 0x10,
    "odr": 0x14,
    "bsrr": 0x18,
}

STM32_PINS = {
    "pin_masks": {
        "PIN0": 0x0001,
        "PIN1": 0x0002,
        "PIN2": 0x0004,
        "PIN3": 0x0008,
        "PIN4": 0x0010,
        "PIN5": 0x0020,
        "PIN6": 0x0040,
        "PIN7": 0x0080,
        "PIN8": 0x0100,
        "PIN9": 0x0200,
        "PIN10": 0x0400,
        "PIN11": 0x0800,
        "PIN12": 0x1000,
        "PIN13": 0x2000,
        "PIN14": 0x4000,
        "PIN15": 0x8000,
    },
    "leds": {"RED": 0x0001, "GREEN": 0x0002, "BLUE": 0x0004},
    "switches": {"BTN_USER": 0x0001},
}

STM32_SYSCTL = {
    "base": 0x40023800,
    "registers": {
        "rcc_ahb1enr": 0x30,
        "rcc_apb2enr": 0x44,
        "rcc_apb1enr": 0x40,
        "rcc_cfgr": 0x04,
    },
}

STM32_NVIC = {
    "irq": {
        "GPIO_EXTI0": 6,
        "GPIO_EXTI1": 7,
        "GPIO_EXTI2": 8,
        "GPIO_EXTI3": 9,
        "GPIO_EXTI4": 10,
        "GPIO_EXTI5_9": 23,
        "GPIO_EXTI10_15": 40,
    },
    "irq_offset": 16,
}


@pytest.fixture
def valid_simulator_config_dict():
    """
    Fixture providing a complete valid simulator configuration dictionary.
    """
    return {
        "memory": MEMORY_CFG,
        "gpio": {
            "kind": "tm4c123",
            "port_size": 0x1000,
            "ports": GPIO_PORTS,
            "offsets": GPIO_OFFSETS,
        },
        "sysctl": SYSCTL_CFG,
        "pins": PINS_CFG,
        "nvic": NVIC_CFG,
    }


@pytest.fixture
def temp_config_yaml_file(temp_yaml_file, valid_simulator_config_dict):
    """
    Fixture that creates a temporary YAML file with valid configuration.

    Args:
        temp_yaml_file: Path object for temporary file
        valid_simulator_config_dict: Valid configuration dictionary

    Yields:
        Path: Path to the temporary YAML file with valid configuration
    """
    with open(temp_yaml_file, "w", encoding="utf-8") as f:
        yaml.dump(valid_simulator_config_dict, f)

    yield temp_yaml_file


@pytest.fixture
def minimal_simulator_config_dict():
    """
    Fixture providing a minimal valid simulator configuration dictionary.

    Returns:
        dict: A minimal configuration with only required fields
    """
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
            "ports": {"A": 0x40004000},
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


@pytest.fixture
def valid_stm32_config_dict():
    """
    Fixture providing a complete valid STM32 simulator configuration dictionary.
    """
    return {
        "memory": {
            "flash_base": 0x08000000,
            "flash_size": 1048576,
            "sram_base": 0x20000000,
            "sram_size": 192000,
            "periph_base": 0x40000000,
            "periph_size": 0x00100000,
            "bitband_sram_base": 0x22000000,
            "bitband_sram_size": 0x02000000,
            "bitband_periph_base": 0x42000000,
            "bitband_periph_size": 0x02000000,
        },
        "gpio": {
            "kind": "stm32",
            "port_size": 0x400,
            "ports": STM32_GPIO_PORTS,
            "offsets": STM32_GPIO_OFFSETS,
        },
        "sysctl": STM32_SYSCTL,
        "pins": STM32_PINS,
        "nvic": STM32_NVIC,
    }


def pytest_configure(config):
    """
    Hook for initial pytest configuration.

    Used to add custom markers and configuration.
    """
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """
    Hook to automatically mark test items.
    """
    # You can add automatic markers here if needed
    pass
