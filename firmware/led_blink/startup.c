#include <stdint.h>

/* `main` is defined in another file */
extern int main(void);

/* Symbols provided by the linker script (linker.ld) */
extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

/* Function declarations */
void Reset_Handler(void);
void Default_Handler(void);

/* Vector table: first two entries are:
 * [0] - initial stack pointer (SP)
 * [1] - address of the Reset_Handler
 */
__attribute__((used, section(".isr_vector")))
uint32_t vector_table[] = {
    (uint32_t)&_estack,       /* 0: initial stack pointer */
    (uint32_t)Reset_Handler,  /* 1: reset handler */
    /* Additional interrupt vectors can be added here if needed */
};

void Reset_Handler(void)
{
    /* Copy initialized data from FLASH to RAM */
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }

    /* Zero-initialize the .bss section */
    dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0;
    }

    /* Call `main` */
    (void)main();

    /* If `main` returns, loop indefinitely */
    while (1) {
    }
}

void Default_Handler(void)
{
    /* Default handler for interrupts that are not defined */
    while (1) {
    }
}
