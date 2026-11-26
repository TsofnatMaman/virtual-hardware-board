/* linker.ld - linker script for the STM32F4 Discovery (STM32F407VG) firmware */

/* NOTE:
 * The STM32F407VG has 1 MB FLASH and 128 KB RAM (plus 64 KB CCM, unused here).
 * Adjust the lengths if your exact STM32F4 variant differs.
 */

MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}

/* Pointer to the top of the stack (end of RAM minus 4 to avoid overflow) */
_estack = ORIGIN(RAM) + LENGTH(RAM) - 4;

/* Optional - harmless */
ENTRY(Reset_Handler)

SECTIONS
{
  /* Vector table - must be first in FLASH */
  .isr_vector :
  {
    . = ALIGN(4);
    KEEP(*(.isr_vector))
    . = ALIGN(4);
  } > FLASH

  /* Code and read-only data */
  .text :
  {
    . = ALIGN(4);
    _stext = .;
    *(.text*)
    *(.rodata*)
    . = ALIGN(4);
    _etext = .;
  } > FLASH

  /* Initialized data - stored in FLASH, executed from RAM */
  .data : AT (ADDR(.text) + SIZEOF(.text))
  {
    . = ALIGN(4);
    _sidata = LOADADDR(.data);  /* source in FLASH */
    _sdata  = .;                /* start address in RAM */
    *(.data*)
    . = ALIGN(4);
    _edata = .;                 /* end of data */
  } > RAM

  /* BSS - zero-initialized data in RAM */
  .bss :
  {
    . = ALIGN(4);
    _sbss = .;
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } > RAM
}
