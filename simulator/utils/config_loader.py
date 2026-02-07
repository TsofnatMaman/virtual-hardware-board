"""Helpers for loading and caching simulator board configuration."""

# pylint: disable=invalid-name,too-many-instance-attributes
# pylint: disable=missing-class-docstring,import-error,global-statement

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml  # type: ignore[import-untyped]

from ..core.exceptions import ConfigurationError


@dataclass(frozen=True)
class Memory_Config:
    flash_base: int
    flash_size: int
    sram_base: int
    sram_size: int
    periph_base: int
    periph_size: int
    bitband_base: int
    bitband_size: int


@dataclass(frozen=True)
class Util_Config:
    mask_32bit: int
    mask_8bit: int


@dataclass(frozen=True)
class GPIO_Offsets:
    data: int
    dir: int
    den: int
    lock: int
    cr: int
    is_: int
    ibe: int
    iev: int
    im: int
    ris: int
    mis: int
    icr: int
    afsel: int


@dataclass(frozen=True)
class GPIO_Config:
    ports: dict[str, int]
    offsets: GPIO_Offsets


@dataclass(frozen=True)
class SysCtl_Config:
    base: int
    registers: dict[str, int]


@dataclass(frozen=True)
class Pins_Config:
    pin_masks: dict[str, int]
    leds: dict[str, int]
    switches: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class NVIC_Config:
    irq: dict[str, int]
    irq_offset: int


@dataclass(frozen=True)
class Simulator_Config:
    memory: Memory_Config
    util: Util_Config
    gpio: GPIO_Config
    sysctl: SysCtl_Config
    pins: Pins_Config
    nvic: NVIC_Config


_LOADER_CONFIG: Optional[Simulator_Config] = None


def _ensure_yaml_available() -> None:
    if yaml is None:
        raise ConfigurationError(
            "PyYAML is required to load simulator config files. Install 'pyyaml'."
        )


def _get_config_path(board_name: str, path: Optional[str] = None) -> str:
    if path is None:
        # Config files are in simulator/{board_name}/config.yaml
        base = Path(__file__).parent.parent / board_name / "config.yaml"
        path = str(base)

    return path


def _load_yaml_file(path: Path) -> dict[str, Any]:
    _ensure_yaml_available()
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except Exception as exc:
        raise ConfigurationError(f"Failed to parse config: {exc}") from exc

    return raw


def _build_nvic_cfg(nvic_raw: dict[str, Any]) -> NVIC_Config:
    """Convert NVIC section to NVIC_Config with defaults."""
    return NVIC_Config(
        irq={k: int(v) for k, v in nvic_raw.get("irq", {}).items()},
        irq_offset=int(nvic_raw.get("irq_offset", 16)),
    )


def _build_gpio_offsets_cfg(offsets_raw: dict[str, Any]) -> GPIO_Offsets:
    """Convert GPIO offsets section to GPIO_Offsets dataclass.
    
    Renames 'is' key to 'is_' since 'is' is a Python keyword.
    """
    offsets_dict = {k: int(v) for k, v in offsets_raw.items()}
    # Handle 'is' keyword by renaming to 'is_'
    if "is" in offsets_dict:
        offsets_dict["is_"] = offsets_dict.pop("is")
    return GPIO_Offsets(**offsets_dict)


def _parse_simulator_cfg_from_dict(raw: dict[str, Any]) -> Simulator_Config:
    try:
        mem = raw["memory"]
        util = raw["util"]
        gpio = raw["gpio"]
        sysctl = raw["sysctl"]
        pins = raw["pins"]
        nvic_raw = raw.get("nvic", {})

        cfg = Simulator_Config(
            memory=Memory_Config(**mem),
            util=Util_Config(**util),
            gpio=GPIO_Config(
                ports={k: int(v) for k, v in gpio["ports"].items()},
                offsets=_build_gpio_offsets_cfg(gpio["offsets"]),
            ),
            sysctl=SysCtl_Config(
                base=int(sysctl["base"]),
                registers={k: int(v) for k, v in sysctl["registers"].items()},
            ),
            pins=Pins_Config(
                pin_masks={k: int(v) for k, v in pins["pin_masks"].items()},
                leds={k: int(v) for k, v in pins["leds"].items()},
                switches={k: int(v) for k, v in pins["switches"].items()},
            ),
            nvic=_build_nvic_cfg(nvic_raw),
        )
    except KeyError as exc:
        raise ConfigurationError(f"Missing required config key: {exc}") from exc
    except TypeError as exc:
        raise ConfigurationError(f"Invalid config schema: {exc}") from exc

    return cfg


def load_config(board_name: str, path: Optional[str] = None) -> Simulator_Config:
    """Load and validate configuration from a YAML file.

    Args:
        path: Optional path to YAML config. if None, load bundled default.

    Returns:
        Simulator_Config instance

    Raise:
        ConfigurationError: on parse or validation errors
    """

    p = Path(_get_config_path(board_name=board_name, path=path))
    raw = _load_yaml_file(p)

    return _parse_simulator_cfg_from_dict(raw=raw)


def get_config(board_name: str) -> Simulator_Config:
    """Return the loaded config, loading default if necessary."""
    global _LOADER_CONFIG
    if _LOADER_CONFIG is None:
        _LOADER_CONFIG = load_config(board_name=board_name)
    assert _LOADER_CONFIG is not None
    return _LOADER_CONFIG
