"""Helpers for loading and validating simulator board configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Literal, Union
import threading

import yaml  # type: ignore[import-untyped]

from simulator.core.exceptions import ConfigurationError


@dataclass(frozen=True)
class MemoryConfig:
    flash_base: int
    flash_size: int
    sram_base: int
    sram_size: int
    periph_base: int
    periph_size: int
    bitband_sram_base: int
    bitband_sram_size: int
    bitband_periph_base: int
    bitband_periph_size: int


@dataclass(frozen=True)
class Tm4cGpioOffsets:
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
class Stm32GpioOffsets:
    idr: int
    odr: int
    bsrr: int


@dataclass(frozen=True)
class Tm4cGpioConfig:
    kind: Literal["tm4c123"]
    ports: dict[str, int]
    offsets: Tm4cGpioOffsets


@dataclass(frozen=True)
class Stm32GpioConfig:
    kind: Literal["stm32"]
    ports: dict[str, int]
    offsets: Stm32GpioOffsets


GpioConfig = Union[Tm4cGpioConfig, Stm32GpioConfig]


@dataclass(frozen=True)
class SysCtlConfig:
    base: int
    registers: dict[str, int]


@dataclass(frozen=True)
class PinsConfig:
    pin_masks: dict[str, int]
    leds: dict[str, int]
    switches: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class NvicConfig:
    irq: dict[str, int]
    irq_offset: int


@dataclass(frozen=True)
class SimulatorConfig:
    memory: MemoryConfig
    gpio: GpioConfig
    sysctl: SysCtlConfig
    pins: PinsConfig
    nvic: NvicConfig


# Configuration cache with thread safety
_LOADER_CACHE: dict[str, SimulatorConfig] = {}
_CACHE_LOCK = threading.RLock()


def _get_config_path(board_name: str, path: Optional[str] = None) -> str:
    if path is None:
        # Config files are in simulator/{board_name}/config.yaml
        base = Path(__file__).parent.parent / board_name / "config.yaml"
        path = str(base)

    return path


def _load_yaml_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except Exception as exc:
        raise ConfigurationError(f"Failed to parse config: {exc}") from exc

    return raw


def _build_nvic_cfg(nvic_raw: dict[str, Any]) -> NvicConfig:
    """Convert NVIC section to NVIC_Config with defaults."""
    return NvicConfig(
        irq={k: int(v) for k, v in nvic_raw.get("irq", {}).items()},
        irq_offset=int(nvic_raw.get("irq_offset", 16)),
    )


def _build_tm4c_gpio_offsets(offsets_raw: dict[str, Any]) -> Tm4cGpioOffsets:
    offsets_dict = {k: int(v) for k, v in offsets_raw.items()}
    if "is" in offsets_dict:
        offsets_dict["is_"] = offsets_dict.pop("is")
    return Tm4cGpioOffsets(**offsets_dict)


def _build_stm32_gpio_offsets(offsets_raw: dict[str, Any]) -> Stm32GpioOffsets:
    offsets_dict = {k: int(v) for k, v in offsets_raw.items()}
    return Stm32GpioOffsets(**offsets_dict)


def _parse_simulator_cfg_from_dict(raw: dict[str, Any]) -> SimulatorConfig:
    try:
        mem = raw["memory"]
        gpio = raw["gpio"]
        sysctl = raw["sysctl"]
        pins = raw["pins"]
        nvic_raw = raw.get("nvic", {})

        cfg = SimulatorConfig(
            memory=MemoryConfig(**mem),
            gpio=_build_gpio_config(gpio),
            sysctl=SysCtlConfig(
                base=int(sysctl["base"]),
                registers={k: int(v) for k, v in sysctl["registers"].items()},
            ),
            pins=PinsConfig(
                pin_masks={k: int(v) for k, v in pins["pin_masks"].items()},
                leds={k: int(v) for k, v in pins["leds"].items()},
                switches={k: int(v) for k, v in pins.get("switches", {}).items()},
            ),
            nvic=_build_nvic_cfg(nvic_raw),
        )
    except KeyError as exc:
        raise ConfigurationError(f"Missing required config key: {exc}") from exc
    except TypeError as exc:
        raise ConfigurationError(f"Invalid config schema: {exc}") from exc

    _validate_memory_config(cfg.memory)
    return cfg


def _build_gpio_config(gpio_raw: dict[str, Any]) -> GpioConfig:
    kind = gpio_raw.get("kind")
    ports = {k: int(v) for k, v in gpio_raw["ports"].items()}
    offsets_raw = gpio_raw["offsets"]

    if kind == "tm4c123":
        return Tm4cGpioConfig(
            kind="tm4c123",
            ports=ports,
            offsets=_build_tm4c_gpio_offsets(offsets_raw),
        )
    if kind == "stm32":
        return Stm32GpioConfig(
            kind="stm32",
            ports=ports,
            offsets=_build_stm32_gpio_offsets(offsets_raw),
        )

    raise ConfigurationError("gpio.kind must be 'stm32' or 'tm4c123'")


def _validate_memory_config(mem: MemoryConfig) -> None:
    """Basic sanity checks for memory layout to fail fast on bad configs."""
    if mem.flash_size <= 0 or mem.sram_size <= 0 or mem.periph_size <= 0:
        raise ConfigurationError("memory sizes must be positive")

    if mem.bitband_sram_size <= 0 or mem.bitband_periph_size <= 0:
        raise ConfigurationError("bit-band alias sizes must be positive")

    # Peripheral window must not overlap flash or sram
    def overlaps(a_base: int, a_size: int, b_base: int, b_size: int) -> bool:
        return not (a_base + a_size <= b_base or b_base + b_size <= a_base)

    if overlaps(mem.periph_base, mem.periph_size, mem.flash_base, mem.flash_size):
        raise ConfigurationError("peripheral window overlaps flash")
    if overlaps(mem.periph_base, mem.periph_size, mem.sram_base, mem.sram_size):
        raise ConfigurationError("peripheral window overlaps sram")

    # Bit-band aliases must not overlap core memory windows
    if overlaps(mem.bitband_sram_base, mem.bitband_sram_size, mem.flash_base, mem.flash_size):
        raise ConfigurationError("SRAM bit-band alias overlaps flash")
    if overlaps(mem.bitband_sram_base, mem.bitband_sram_size, mem.sram_base, mem.sram_size):
        raise ConfigurationError("SRAM bit-band alias overlaps SRAM window")
    if overlaps(mem.bitband_periph_base, mem.bitband_periph_size, mem.flash_base, mem.flash_size):
        raise ConfigurationError("Peripheral bit-band alias overlaps flash")
    if overlaps(mem.bitband_periph_base, mem.bitband_periph_size, mem.sram_base, mem.sram_size):
        raise ConfigurationError("Peripheral bit-band alias overlaps SRAM")

    # Alias windows may be larger than the actual underlying regions; bounds are
    # enforced at access time.


def load_config(board_name: str, path: Optional[str] = None) -> SimulatorConfig:
    """Load and validate configuration from a YAML file.

    Args:
        board_name: Board identifier (e.g., 'stm32', 'tm4c123') for config lookup.
        path: Optional path to YAML config. If None, load bundled simulator/{board_name}/config.yaml.

    Returns:
        SimulatorConfig instance

    Raises:
        ConfigurationError: on parse or validation errors
    """

    p = Path(_get_config_path(board_name=board_name, path=path))
    raw = _load_yaml_file(p)

    return _parse_simulator_cfg_from_dict(raw=raw)


def get_config(board_name: str) -> SimulatorConfig:
    """Return the loaded config for board_name, loading and caching if necessary.

    Configs are cached per board_name; repeated calls for the same board
    return the cached instance without re-reading the YAML file.
    
    THREAD SAFETY: This function is thread-safe. Multiple threads can
    safely call this concurrently.
    """
    with _CACHE_LOCK:
        if board_name not in _LOADER_CACHE:
            _LOADER_CACHE[board_name] = load_config(board_name=board_name)
        return _LOADER_CACHE[board_name]


def clear_config_cache() -> None:
    """Clear all cached configurations.
    
    Useful for testing or resetting state between board resets.
    All subsequent calls to get_config() will reload from disk.
    """
    with _CACHE_LOCK:
        _LOADER_CACHE.clear()
