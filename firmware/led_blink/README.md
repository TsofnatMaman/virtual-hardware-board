# LED Blink Example Firmware

Simple example firmware that demonstrates GPIO control on the TM4C123.

## Features

- Initializes GPIO Port F
- Controls RGB LED (Red, Green, Blue)
- Implements delay loops
- Demonstrates memory-mapped I/O

## Files

- `main.c` - Main application code
- `startup.c` - Startup code and vector table
- `tm4c.h` - Hardware register definitions
- `linker.ld` - Linker script for memory layout
- `Makefile` - Build system

## Building

### Prerequisites

Install the ARM GCC toolchain:

**Ubuntu/Debian:**
```bash
sudo apt-get install gcc-arm-none-eabi
```

**macOS:**
```bash
brew install arm-none-eabi-gcc
```

**Windows:**
Download from: <https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm>

### Compile

```bash
make
```

This produces `firmware.bin` which can be loaded into the simulator.

### Clean

```bash
make clean
```

## Code Overview

### Main Function

```c
int main(void) {
    // Enable GPIO Port F clock
    SYSCTL_RCGCGPIO_R |= (1U << 5);
    
    // Configure pins as outputs
    GPIO_PORTF_DIR_R |= (LED_RED | LED_BLUE | LED_GREEN);
    GPIO_PORTF_DEN_R |= (LED_RED | LED_BLUE | LED_GREEN);
    
    // Turn on blue LED (static)
    GPIO_PORTF_DATA_R |= LED_BLUE;
    
    // Blink red LED
    while (1) {
        GPIO_PORTF_DATA_R |= LED_RED;   // On
        delay();
        GPIO_PORTF_DATA_R &= ~LED_RED;  // Off
        delay();
    }
}
```

### Memory Map

```
0x00000000 - 0x0007FFFF : Flash ROM (512 KB)
0x20000000 - 0x2001FFFF : SRAM (128 KB)
0x40000000 - 0x400FFFFF : Peripherals
0x400FE608            : SYSCTL_RCGCGPIO (GPIO Clock Gate)
0x40025000            : GPIO Port F Base
```

### Port F Pins

- **PF0**: SW2 (button, requires unlock)
- **PF1**: Red LED
- **PF2**: Blue LED
- **PF3**: Green LED
- **PF4**: SW1 (button)

## Running in Simulator

```bash
# GUI mode
python -m simulator.main --binary firmware.bin

# Headless mode
python -m simulator.main --binary firmware.bin --mode headless --steps 100
```

## Expected Behavior

When run in the simulator:
1. Blue LED turns on immediately (stays on)
2. Red LED blinks on and off repeatedly
3. Delay between state changes

## Modifications

Try these modifications to experiment:

### 1. Change Blink Rate

Modify the delay loop counter:
```c
while (counter < 200000) {  // Slower
    ++counter;
}
```

### 2. Blink Different LEDs

```c
GPIO_PORTF_DATA_R ^= LED_GREEN;  // Toggle green
```

### 3. Create Patterns

```c
// Cycle through colors
GPIO_PORTF_DATA_R = LED_RED;
delay();
GPIO_PORTF_DATA_R = LED_GREEN;
delay();
GPIO_PORTF_DATA_R = LED_BLUE;
delay();
```

### 4. Use All LEDs (White Light)

```c
GPIO_PORTF_DATA_R = LED_RED | LED_GREEN | LED_BLUE;
```

## Troubleshooting

**Q: LEDs don't turn on**

A: Check that:
- GPIO clock is enabled (`SYSCTL_RCGCGPIO_R`)
- Pins are configured as outputs (`GPIO_PORTF_DIR_R`)
- Digital function is enabled (`GPIO_PORTF_DEN_R`)

**Q: Code doesn't execute**

A: Verify:
- Firmware compiled without errors
- Vector table is properly formatted
- Stack pointer points to valid RAM

## Resources

- [TM4C123GH6PM Datasheet](https://www.ti.com/product/TM4C123GH6PM)
- [Tiva C Series User's Guide](https://www.ti.com/lit/ug/spmu296/spmu296.pdf)
- [ARM Cortex-M3 Guide](https://developer.arm.com/documentation/ddi0337/)
