# Minimal Cortex-M build for the Virtual Hardware Board simulator.
#
#   make                      # builds build/app.elf for BOARD=tm4c123
#   make BOARD=stm32c031      # builds for the STM32C031 board
#
# All src/*.c files are compiled. Board register headers are in board/<BOARD>/.

BOARD ?= tm4c123
TOOLCHAIN ?= arm-none-eabi-

ifeq ($(BOARD),tm4c123)
CPU := cortex-m3
else ifeq ($(BOARD),stm32c031)
CPU := cortex-m0plus
else
$(error Unknown BOARD '$(BOARD)'. Use tm4c123 or stm32c031)
endif

SRCS    := board/startup.c $(wildcard src/*.c)
ELF     := build/app.elf
BIN     := build/app.bin
CFLAGS  := -mcpu=$(CPU) -mthumb -Os -g -ffreestanding -nostdlib -Wall -Wextra \
           -Iboard/$(BOARD) -Isrc
LDFLAGS := -T board/$(BOARD)/linker.ld -Wl,-Map=build/app.map -Wl,--gc-sections

all: $(BIN)

$(ELF): $(SRCS) board/$(BOARD)/linker.ld
	@mkdir -p build
	$(TOOLCHAIN)gcc $(CFLAGS) $(LDFLAGS) $(SRCS) -o $@
	-$(TOOLCHAIN)size $@

$(BIN): $(ELF)
	$(TOOLCHAIN)objcopy -O binary $< $@

clean:
	rm -rf build

.PHONY: all clean
