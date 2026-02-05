# Makefile for TM4C123 firmware compilation

# Toolchain
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# Target
TARGET = firmware

# Source files
SRCS = main.c startup.c
OBJS = $(SRCS:.c=.o)

# Compiler flags
CFLAGS = -mcpu=cortex-m3
CFLAGS += -mthumb
CFLAGS += -Os
CFLAGS += -ffreestanding
CFLAGS += -nostdlib
CFLAGS += -Wall
CFLAGS += -Wextra
CFLAGS += -g

# Linker flags
LDFLAGS = -T linker.ld
LDFLAGS += -Wl,-Map=$(TARGET).map
LDFLAGS += -Wl,--gc-sections

# Default target
all: $(TARGET).bin

# Compile C files
%.o: %.c
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

# Link to create ELF
$(TARGET).elf: $(OBJS)
	@echo "Linking..."
	$(CC) $(CFLAGS) $(LDFLAGS) $(OBJS) -o $@
	@echo "Size information:"
	$(SIZE) $@

# Convert ELF to binary
$(TARGET).bin: $(TARGET).elf
	@echo "Creating binary..."
	$(OBJCOPY) -O binary $< $@
	@echo "✓ Firmware ready: $(TARGET).bin"

# Clean build artifacts
clean:
	@echo "Cleaning..."
	rm -f $(OBJS) $(TARGET).elf $(TARGET).bin $(TARGET).map
	@echo "✓ Clean complete"

# Rebuild everything
rebuild: clean all

# Show help
help:
	@echo "TM4C123 Firmware Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all     - Build firmware (default)"
	@echo "  clean   - Remove build artifacts"
	@echo "  rebuild - Clean and build"
	@echo "  help    - Show this help"
	@echo ""
	@echo "Requirements:"
	@echo "  arm-none-eabi-gcc toolchain"

.PHONY: all clean rebuild help
