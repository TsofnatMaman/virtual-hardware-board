/* Running light on the four user LEDs of the STM32F4 Discovery board
 * (LD4 green PD12 -> LD3 orange PD13 -> LD5 red PD14 -> LD6 blue PD15). */

#include "stm32f4.h"

#define LED_FIRST_PIN  12U
#define LED_COUNT      4U

static void delay(int count)
{
    volatile int i = 0;
    while (i < count) {
        ++i;
    }
}

int main(void)
{
    unsigned int led = 0;

    /* enable the clock of GPIO port D */
    RCC_AHB1ENR_R |= RCC_AHB1ENR_GPIODEN;

    /* PD12..PD15 as general purpose outputs (MODER = 01) */
    for (unsigned int pin = LED_FIRST_PIN; pin < LED_FIRST_PIN + LED_COUNT; ++pin) {
        GPIOD_MODER_R &= ~(3U << (2U * pin));
        GPIOD_MODER_R |=  (1U << (2U * pin));
    }

    while (1) {
        /* one LED on, all the others off, in a single atomic BSRR write */
        unsigned int on_pin = LED_FIRST_PIN + led;
        GPIOD_BSRR_R = (0xFU << (LED_FIRST_PIN + 16U)) | (1U << on_pin);
        delay(1500);
        led = (led + 1U) % LED_COUNT;
    }
}
