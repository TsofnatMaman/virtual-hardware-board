from dataclasses import dataclass, field

from typing import Dict, Optional, Any
import yaml
from pathlib import Path

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
    icr: int

@dataclass(frozen=True)
class GPIO_Config:
    ports: Dict[str, int]
    offsets: GPIO_Offsets

@dataclass(frozen=True)
class SysCtl_Config:
    base: int
    registers: Dict[str, int]

@dataclass(frozen=True)
class Pins_Config:
    pin_masks: Dict[str, int]
    leds: Dict[str, int]
    switches: Dict[str, int] = field(default_factory=dict)

@dataclass(frozen=True)
class NVIC_Config:
    irq: Dict[str, int]
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
            "PyYAML is required to load simulator config files. "
            "Install 'pyyaml'."
        )

def _get_config_path(board_name: str, path: Optional[str] = None) -> str:
    if path is None:
        base = (
            Path(__file__).parent
            / board_name
            / "config.yaml"
        )
        path = str(base)
    
    return path

def _load_yaml_file(path: Path) -> Dict[str, Any]:
    _ensure_yaml_available()
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to parse config: {exc}"
        ) from exc
    
    return raw

def _parse_simulator_cfg_from_dict(raw: Dict[str, Any]) -> Simulator_Config:
    try:
        mem = raw["memory"]
        util = raw["util"]
        gpio = raw["gpio"]
        sysctl = raw["sysctl"]
        pins = raw["pins"]
        nvic = raw.get("nvic", {})

        cfg = Simulator_Config(
            memory = Memory_Config(**mem),
            util = Util_Config(**util),
            gpio = GPIO_Config(
                ports = {k: int(v) for k,v in gpio["ports"].items()},
                offsets = GPIO_Offsets(**gpio["offsets"]),
            ),
            sysctl = SysCtl_Config(
                base=int(sysctl["base"]),
                registers={k:int(v) for k,v in sysctl["registers"].items()},
            ),
            pins = Pins_Config(
                pin_masks = {k: int(v) for k, v in pins["pin_masks"].items()},
                leds = {k: int(v) for k,v in pins["leds"].items()},
                switches = {k: int(v) for k, v in pins["switches"].items()},
            ),
            nvic = NVIC_Config(
                irq = {k: int(v) for k, v in nvic.get("irq", {}).items()},
                irq_offset=int(nvic.get("irq_offset", 16)),
            ),
        )
    except KeyError as exc:
        raise ConfigurationError(
            f"Missing required config key: {exc}"
        ) from exc
    except TypeError as exc:
        raise ConfigurationError(
            f"Invalid config schema: {exc}"
        ) from exc
        
    return cfg

def load_config(
        board_name: str, path: Optional[str] = None
) -> Simulator_Config:
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
    if _LOADER_CONFIG is None:
        return load_config(board_name=board_name)
    return _LOADER_CONFIG