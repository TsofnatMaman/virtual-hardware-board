//=================================================================
// Minimal register definitions for the STM32F407 (STM32F4 Discovery)
// used by the simulator examples. NOT a complete header.
//
// STM32F4DISCOVERY user LEDs (all on GPIOD):
//   LD4 green  = PD12     LD3 orange = PD13
//   LD5 red    = PD14     LD6 blue   = PD15
//=================================================================

#ifndef STM32F4_H__
#define STM32F4_H__

#define RCC_AHB1ENR_R    (*((volatile unsigned int *)0x40023830U))

#define GPIOD_MODER_R    (*((volatile unsigned int *)0x40020C00U))
#define GPIOD_OTYPER_R   (*((volatile unsigned int *)0x40020C04U))
#define GPIOD_OSPEEDR_R  (*((volatile unsigned int *)0x40020C08U))
#define GPIOD_PUPDR_R    (*((volatile unsigned int *)0x40020C0CU))
#define GPIOD_IDR_R      (*((volatile unsigned int *)0x40020C10U))
#define GPIOD_ODR_R      (*((volatile unsigned int *)0x40020C14U))
#define GPIOD_BSRR_R     (*((volatile unsigned int *)0x40020C18U))

#define RCC_AHB1ENR_GPIODEN  (1U << 3U)

#endif // STM32F4_H__
