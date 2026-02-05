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


@pytest.fixture
def valid_simulator_config_dict():
    """
    Fixture providing a complete valid simulator configuration dictionary.

    Returns:
        dict: A complete configuration for the Simulator_Config
    """
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
            "ports": {
                "A": 0x40004000,
                "B": 0x40005000,
                "C": 0x40006000,
                "D": 0x40007000,
                "E": 0x40024000,
                "F": 0x40025000,
            },
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
                "rcgcuart": 0x618,
                "rcgcssi": 0x61C,
                "rcgci2c": 0x620,
                "rcgcpwm": 0x640,
                "rcgcadc": 0x638,
            },
        },
        "pins": {
            "pin_masks": {
                "PIN0": 0x01,
                "PIN1": 0x02,
                "PIN2": 0x04,
                "PIN3": 0x08,
                "PIN4": 0x10,
                "PIN5": 0x20,
                "PIN6": 0x40,
            },
            "leds": {
                "LED1": 0x01,
                "LED2": 0x02,
            },
            "switches": {
                "SW1": 0x01,
                "SW2": 0x02,
            },
        },
        "nvic": {
            "irq": {
                "timer": 19,
                "gpio": 0,
            },
            "irq_offset": 16,
        },
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
