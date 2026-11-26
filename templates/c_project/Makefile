# Minimal Cortex-M build for the Virtual Hardware Board simulator.
#
#   make                      # builds build/app.elf for BOARD=tm4c123
#   make BOARD=stm32c031      # builds for the STM32C031 board
#
# All src/*.c files are compiled. Board register headers are in board/<BOARD>/.

BOARD ?= tm4c123
# No optimisation: variables and functions stay easy to debug (use OPT=-Os for size).
OPT ?= -O0
# Extra compiler flags from the command line, e.g. EXTRA_CFLAGS=-Werror in CI.
EXTRA_CFLAGS ?=
TOOLCHAIN ?= arm-none-eabi-

ifeq ($(BOARD),tm4c123)
CPU := cortex-m3
else ifeq ($(BOARD),stm32c031)
CPU := cortex-m0plus
else ifeq ($(BOARD),stm32f4)
CPU := cortex-m4
else
$(error Unknown BOARD '$(BOARD)'. Use tm4c123, stm32c031 or stm32f4)
endif

SRCS    := board/startup.c $(wildcard src/*.c)
ELF     := build/app.elf
BIN     := build/app.bin
CFLAGS  := -mcpu=$(CPU) -mthumb $(OPT) -g -ffreestanding -nostdlib -Wall -Wextra \
           -Iboard/$(BOARD) -Isrc $(EXTRA_CFLAGS)
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
