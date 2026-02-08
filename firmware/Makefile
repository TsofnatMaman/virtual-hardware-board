# Unified firmware build (single command)
#
# Usage:
#   make BOARD=tm4c123 MAIN=led_blink/tm4c/main.c
#   make BOARD=stm32c031 MAIN=led_blink/stm32/main.c OUT=build/my_app.bin
#
# From repo root:
#   make -f firmware/Makefile BOARD=tm4c123 MAIN=firmware/led_blink/tm4c/main.c

# Toolchain
# If CC/OBJCOPY/SIZE are set in the environment, they might point to host tools
# (e.g. "cc"). Override those unless the user explicitly sets them on the
# command line.
TOOLCHAIN ?= arm-none-eabi-
ifneq ($(origin CC), command line)
CC := $(TOOLCHAIN)gcc
endif
ifneq ($(origin OBJCOPY), command line)
OBJCOPY := $(TOOLCHAIN)objcopy
endif
ifneq ($(origin SIZE), command line)
SIZE := $(TOOLCHAIN)size
endif

FIRMWARE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

BOARD ?=
MAIN ?=
OUT ?=

ifeq ($(strip $(BOARD)),)
$(error BOARD is required. Example: BOARD=tm4c123 or BOARD=stm32c031)
endif
ifeq ($(strip $(MAIN)),)
$(error MAIN is required. Example: MAIN=led_blink/tm4c/main.c)
endif

ifeq ($(BOARD),tm4c123)
CPU := cortex-m3
BOARD_DIR := $(FIRMWARE_DIR)/boards/tm4c123
else ifeq ($(BOARD),stm32c031)
CPU := cortex-m0plus
BOARD_DIR := $(FIRMWARE_DIR)/boards/stm32c031
else
$(error Unknown BOARD '$(BOARD)'. Supported: tm4c123, stm32c031)
endif

MAIN_ABS := $(abspath $(MAIN))
STARTUP ?= $(FIRMWARE_DIR)/startup.c
LDSCRIPT := $(BOARD_DIR)/linker.ld

OUT_BIN := $(OUT)
ifeq ($(strip $(OUT_BIN)),)
OUT_BIN := $(dir $(MAIN_ABS))firmware.bin
endif
ifneq ($(suffix $(OUT_BIN)),.bin)
OUT_BIN := $(OUT_BIN).bin
endif

OUT_ELF := $(patsubst %.bin,%.elf,$(OUT_BIN))
OUT_MAP := $(patsubst %.bin,%.map,$(OUT_BIN))

CFLAGS ?=
CFLAGS += -mcpu=$(CPU)
CFLAGS += -mthumb
CFLAGS += -Os
CFLAGS += -ffreestanding
CFLAGS += -nostdlib
CFLAGS += -Wall
CFLAGS += -Wextra
CFLAGS += -g

LDFLAGS ?=
LDFLAGS += -T $(LDSCRIPT)
LDFLAGS += -Wl,-Map=$(OUT_MAP)
LDFLAGS += -Wl,--gc-sections

INCLUDES := -I$(dir $(MAIN_ABS)) -I$(BOARD_DIR)

all: $(OUT_BIN)

$(OUT_BIN): $(MAIN_ABS) $(STARTUP) $(LDSCRIPT)
	@echo "Building $(OUT_BIN) (board=$(BOARD))"
	$(CC) $(CFLAGS) $(LDFLAGS) $(INCLUDES) $(STARTUP) $(MAIN_ABS) -o $(OUT_ELF)
	$(OBJCOPY) -O binary $(OUT_ELF) $(OUT_BIN)
	-$(SIZE) $(OUT_ELF)
	@echo "Done: $(OUT_BIN)"

clean:
	@echo "Cleaning outputs"
	rm -f $(OUT_ELF) $(OUT_BIN) $(OUT_MAP)

help:
	@echo "Unified firmware build"
	@echo ""
	@echo "Usage:"
	@echo "  make BOARD=tm4c123 MAIN=led_blink/tm4c/main.c"
	@echo "  make BOARD=stm32c031 MAIN=led_blink/stm32/main.c OUT=build/my_app.bin"
	@echo ""
	@echo "Boards:"
	@echo "  tm4c123"
	@echo "  stm32c031"

.PHONY: all clean help
