/* tm4c.h */
#ifndef TM4C_H
#define TM4C_H

#include <stdint.h>

// Base addresses and registers for Port F on TM4C123
#define SYSCTL_RCGCGPIO_R  (*((volatile uint32_t *)0x400FE608U))
#define GPIO_PORTF_DIR_R   (*((volatile uint32_t *)0x40025400U))
#define GPIO_PORTF_DEN_R   (*((volatile uint32_t *)0x4002551CU))
#define GPIO_PORTF_DATA_R  (*((volatile uint32_t *)0x400253FCU))

#endif