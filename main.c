/*
 * ====================================================================
 *  Temperature Monitoring & Fan Control System
 *  MCU:      ATmega16 @ 8 MHz
 *  Sensor:   DS18B20 (1-Wire) on pin PA0
 *  Actuator: L298N motor driver -> 5010 cooling fan (PWM via Timer0)
 *  Output:   UART -> Python GUI on PC
 *
 *  Course project - Microprocessors & Microcontrollers (EMA3084E)
 * ====================================================================
 */

#define F_CPU 8000000UL
#include <avr/io.h>
#include <util/delay.h>
#include <stdio.h>
#include <stdint.h>

#define DQ       PA0
#define DQ_DDR   DDRA
#define DQ_PORT  PORTA
#define DQ_PIN   PINA

// ==================== UART ====================

void UART_Init(unsigned int ubrr) {
    UBRRH = (unsigned char)(ubrr >> 8);
    UBRRL = (unsigned char)ubrr;
    UCSRB = (1 << TXEN) | (1 << RXEN);
    UCSRC = (1 << URSEL) | (1 << UCSZ1) | (1 << UCSZ0);
}

void UART_SendChar(char c) {
    while (!(UCSRA & (1 << UDRE)));
    UDR = c;
}

void UART_SendString(char *str) {
    while (*str) UART_SendChar(*str++);
}

// ==================== DS18B20 (1-Wire) ====================

void OneWire_Reset(void) {
    DQ_DDR |= (1 << DQ);
    DQ_PORT &= ~(1 << DQ);
    _delay_us(480);
    DQ_DDR &= ~(1 << DQ);
    _delay_us(480);
}

void OneWire_WriteBit(uint8_t bit) {
    DQ_DDR |= (1 << DQ);
    DQ_PORT &= ~(1 << DQ);
    _delay_us(2);

    if (bit) DQ_DDR &= ~(1 << DQ);
    _delay_us(60);

    DQ_DDR &= ~(1 << DQ);
}

uint8_t OneWire_ReadBit(void) {
    uint8_t bit;

    DQ_DDR |= (1 << DQ);
    DQ_PORT &= ~(1 << DQ);
    _delay_us(2);

    DQ_DDR &= ~(1 << DQ);
    _delay_us(10);

    bit = (DQ_PIN & (1 << DQ)) ? 1 : 0;

    _delay_us(50);
    return bit;
}

void OneWire_WriteByte(uint8_t data) {
    for (uint8_t i = 0; i < 8; i++) {
        OneWire_WriteBit(data & 1);
        data >>= 1;
    }
}

uint8_t OneWire_ReadByte(void) {
    uint8_t data = 0;
    for (uint8_t i = 0; i < 8; i++) {
        if (OneWire_ReadBit()) data |= (1 << i);
    }
    return data;
}

float DS18B20_ReadTemp(void) {
    OneWire_Reset();
    OneWire_WriteByte(0xCC);   // Skip ROM (single sensor on bus)
    OneWire_WriteByte(0x44);   // Convert T
    _delay_ms(750);            // Wait for conversion (12-bit resolution)

    OneWire_Reset();
    OneWire_WriteByte(0xCC);   // Skip ROM
    OneWire_WriteByte(0xBE);   // Read Scratchpad

    uint8_t tempL = OneWire_ReadByte();
    uint8_t tempH = OneWire_ReadByte();

    int16_t raw = (tempH << 8) | tempL;
    return (float)raw * 0.0625f;
}

// ==================== PWM (Timer0, pin PB3 / OC0) ====================

void PWM_Init(void) {
    DDRB |= (1 << PB3);
    // Fast PWM, non-inverting, prescaler = 8
    TCCR0 = (1 << WGM00) | (1 << WGM01) | (1 << COM01) | (1 << CS01);
    OCR0 = 0;
}

// ==================== MAIN ====================

int main(void) {
    // Status LEDs: PC0 = green, PC1 = yellow, PC2 = red
    DDRC |= (1 << PC0) | (1 << PC1) | (1 << PC2);

    // Motor direction via L298N: PB1 = IN1, PB2 = IN2
    DDRB |= (1 << PB1) | (1 << PB2);
    PORTB |= (1 << PB1);
    PORTB &= ~(1 << PB2);

    UART_Init(51);   // ~9600 baud @ 8MHz
    PWM_Init();

    char buffer[100];

    while (1) {
        float temp = DS18B20_ReadTemp();

        // Split integer/decimal parts to display sign correctly
        int t_int = (int)temp;
        float f_part = temp - (float)t_int;
        if (f_part < 0) f_part = -f_part;
        int t_dec = (int)(f_part * 100.0f);

        // Handle -0.xx case (sign lost when cast to int)
        char sign_char[2];
        if (temp < 0 && t_int == 0) {
            sprintf(sign_char, "-");
        } else {
            sprintf(sign_char, "");
        }

        // LED + PWM control based on temperature thresholds
        PORTC &= ~((1 << PC0) | (1 << PC1) | (1 << PC2));
        if (temp >= 40) {
            PORTC |= (1 << PC2);        // Red LED
            OCR0 = 250;
        } else if (temp >= 30) {
            PORTC |= (1 << PC1);        // Yellow LED
            OCR0 = 200;
        } else {
            PORTC |= (1 << PC0);        // Green LED
            OCR0 = (temp < 25) ? 0 : 150;
        }

        // Send data to PC over UART
        sprintf(buffer, "Temp: %s%d.%02d C | PWM: %d\r\n",
                sign_char, t_int, t_dec, OCR0);
        UART_SendString(buffer);

        _delay_ms(500);
    }
}
