# ARM Cortex-M Virtual Hardware Board Simulator

A comprehensive, hardware-faithful simulator for ARM Cortex-M microcontrollers (STM32, TM4C123) with CPU emulation, memory management, and peripheral simulation.

## Quick Start

```python
from simulator import create_board

# Create a board
board = create_board("stm32f4")

# Reset the CPU (loads firmware, sets PC/MSP)
board.cpu.reset()

# Execute one instruction
board.cpu.step()

# Read a peripheral register
gpio_odr = board.address_space.read(0x40020014, 4)

# Reset the board (clears RAM, resets all peripherals)
board.reset()
```

## Supported Boards

- **STM32F4**: ARM Cortex-M4 with 256KB Flash, 64KB SRAM, GPIO peripherals
- **TM4C123**: ARM Cortex-M4F with 256KB Flash, 32KB SRAM, GPIO peripherals

## Architecture

The simulator is built on clean, layered abstractions:

```
┌─────────────────────────────────────────────────────────────┐
│ BOARDS LAYER (complete MCU systems)                         │
│ STM32F4Board, TM4C123Board                                  │
├─────────────────────────────────────────────────────────────┤
│ VENDORS LAYER (MCU-specific peripherals)                    │
│ STM32GPIO, TM4C123GPIO                                      │
├─────────────────────────────────────────────────────────────┤
│ CORE LAYER (hardware abstractions)                          │
│ Register, AddressSpace, CortexM, Unicorn Interface          │
├─────────────────────────────────────────────────────────────┤
│ UTILITIES (configuration, constants, logging)               │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **Single Responsibility**: Each class owns one domain
- **Explicit Hardware Semantics**: Code reads like datasheets
- **Minimal Inheritance**: Composition over inheritance
- **Vendor Isolation**: No shared base classes for GPIO or other peripherals

## Key Concepts

### Register
A typed storage location with read/write behavior. Examples:
- `SimpleRegister`: Plain storage
- `ReadOnlyRegister`: Ignores writes
- `WriteOnlyRegister`: Returns reset value on read
- Custom subclasses: Side effects on read/write

### AddressSpace
Routes CPU memory accesses to the right region:
- Flash (read-only firmware storage)
- SRAM (read-write volatile storage)
- MMIO (dispatch to peripherals)
- Bitband (bit-level access windows)

### Peripheral
Anything at an MMIO address. Implements:
- `read(offset, size)` - read from register
- `write(offset, size, value)` - write to register
- `reset()` - reset to initial state

### Board
A complete MCU system: CPU + memory + peripherals. Created via:
```python
board = create_board("stm32f4")
# or
from simulator.boards import STM32F4Board
board = STM32F4Board()
```

## Usage Examples

### Load Firmware and Run

```python
from simulator import create_board

board = create_board("stm32f4")

# Load firmware into flash
firmware = open("firmware.bin", "rb").read()
board.address_space.flash.load_image(firmware)

# Reset and execute
board.cpu.reset()
for _ in range(100):
    board.cpu.step()

# Check CPU state
pc = board.cpu.get_register(15)  # Program counter
sp = board.cpu.get_register(13)  # Stack pointer
```

### Interact with GPIO

```python
from simulator import create_board
from simulator.interfaces.gpio_enums import PinLevel

board = create_board("stm32f4")

# Get GPIO peripheral
gpio_a = board.peripherals["GPIO_A"]

# Simulate external input (pin pulled high)
gpio_a.set_pin(0, PinLevel.HIGH)

# Check output register
odr = board.address_space.read(0x40020014, 4)
print(f"Output data register: 0x{odr:04X}")

# Check input register
idr = board.address_space.read(0x40020010, 4)
print(f"Input data register: 0x{idr:04X}")
```

### Memory Access

```python
board = create_board("tm4c123")

# Read from different regions
flash_value = board.address_space.read(0x00000000, 4)  # Flash
sram_value = board.address_space.read(0x20000000, 4)   # SRAM
gpio_value = board.address_space.read(0x40004000, 4)   # GPIO

# Write to SRAM
board.address_space.write(0x20000100, 4, 0x12345678)

# Bitband access (atomic bit operations)
# Alias base: 0x22000000, target: SRAM 0x20000000
bitband_alias = 0x22000000 + (0x100 * 32) + (5 * 4)  # Bit 5 of word at 0x20000100
board.address_space.write(bitband_alias, 4, 1)  # Set bit 5
```

### Inspect Memory Layout

```python
board = create_board("stm32f4")

# Get memory map
layout = board.address_space.get_memory_map()
print(f"Flash: {layout['flash']['base']} size {layout['flash']['size']}")
print(f"SRAM: {layout['sram']['base']} size {layout['sram']['size']}")
```

## Testing

The simulator is designed for easy testing:

```python
import pytest
from simulator import create_board
from simulator.interfaces.gpio_enums import PinLevel

def test_gpio_output():
    board = create_board("stm32f4")
    gpio = board.peripherals["GPIO_A"]
    
    # Set output pin high
    gpio.set_pin(0, PinLevel.HIGH)
    
    # Read ODR (output data register)
    odr = board.address_space.read(0x40020014, 4)
    assert odr & 1 == 1

def test_bitband_write():
    board = create_board("stm32f4")
    
    # Write to SRAM via bitband
    addr = 0x22000000  # Bitband SRAM alias base
    board.address_space.write(addr, 4, 1)  # Set bit 0
    
    # Verify via direct SRAM read
    value = board.address_space.read(0x20000000, 4)
    assert value & 1 == 1
```

## Adding a New Microcontroller

To add support for a new MCU (e.g., STM32H7):

1. **Create YAML configuration**: `simulator/stm32h7/config.yaml`
   - Define memory regions (Flash, SRAM, MMIO, bitband)
   - Define GPIO ports and register offsets
   - Define other peripherals

2. **Implement peripherals**: `simulator/peripherals/stm32h7_gpio.py`
   - Create vendor-specific GPIO class
   - Use RegisterFile to manage registers
   - Each peripheral is self-contained (no shared base classes)

3. **Create board class**: `simulator/boards/stm32h7.py`
   - Use factories to create address space and CPU
   - Initialize peripherals
   - Register in board registry

4. **Register the board**: Update `simulator/boards/__init__.py`
   ```python
   from simulator.boards.stm32h7 import STM32H7Board
   register_board("stm32h7", STM32H7Board)
   ```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed guidance.

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** – Detailed architecture guide and design principles
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** – What changed in the redesign, migration guide

## Installation

```bash
pip install -e .
```

Dependencies:
- Python 3.8+
- unicorn (for CPU emulation)
- pyyaml (for configuration)

## Project Structure

```
simulator/
├── core/              # Fundamental abstractions
│   ├── register.py   # Register model
│   ├── address_space.py # Memory regions
│   ├── memmap.py     # Address space dispatcher
│   ├── cpu2.py       # CPU emulation
│   ├── builders.py   # Factories
│   └── board.py      # Board registry
├── boards/           # MCU board implementations
│   ├── stm32f4.py
│   └── tm4c123.py
├── peripherals/      # MCU peripherals
│   ├── stm32_gpio.py
│   └── tm4c_gpio.py
├── interfaces/       # Protocol definitions
├── utils/            # Config, constants, logging
└── __init__.py       # Main entry point

tests/                # Test suite
```

## License

See [LICENSE](LICENSE)

---

**Questions or contributions?** Please refer to the architecture documentation for design principles and coding guidelines.