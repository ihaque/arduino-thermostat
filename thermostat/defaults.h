#ifndef	DEFAULTS_H
#define	DEFAULTS_H

// Pin mappings on Arduino ATMega328P
// #define PIN_NAME Port register, register bit
// These mappings translate Arduino-level pin names to port/bit pairs for
// the C-level macros
#define ARD_PIN_RST C,6
#define ARD_PIN_0   D,0
#define ARD_PIN_RX ARD_PIN_0
#define ARD_PIN_1   D,1
#define ARD_PIN_TX ARD_PIN_1
#define ARD_PIN_2   D,2
#define ARD_PIN_3   D,3
#define ARD_PIN_4   D,4
#define ARD_PIN_XTAL1   B,6
#define ARD_PIN_XTAL2   B,7
#define ARD_PIN_5   D,5
#define ARD_PIN_6   D,6
#define ARD_PIN_7   D,7
#define ARD_PIN_8   B,0
#define ARD_PIN_9   B,1
#define ARD_PIN_10  B,2
#define ARD_PIN_11  B,3
#define ARD_PIN_12  B,4
#define ARD_PIN_13  B,5
#define ARD_PIN_A0  C,0
#define ARD_PIN_A1  C,1
#define ARD_PIN_A2  C,2
#define ARD_PIN_A3  C,3
#define ARD_PIN_A4  C,4
#define ARD_PIN_A5  C,5

#define	P_MOSI	ARD_PIN_11
#define	P_MISO	ARD_PIN_12
#define	P_SCK	ARD_PIN_13

#define	MCP2515_CS			ARD_PIN_10
#define	MCP2515_INT			ARD_PIN_2

// CANBus shield accessory pins
#define CAN_BUS_LCD_TX 6
#define CAN_BUS_SD_CS 9
#define DS18B20_DQ 5

// CANBus shield joystick pins
#define UP      A1
#define RIGHT   A2
#define DOWN    A3
#define CLICK   A4
#define LEFT    A5

#define DS18B20_RESOLUTION_BITS 10

#if (DS18B20_RESOLUTION_BITS == 12)
    #define DS18B20_CONFIG_BYTE 0x7F
    #define DS18B20_TCONV_MS 750 
#elif (DS18B20_RESOLUTION_BITS == 11)
    #define DS18B20_CONFIG_BYTE 0x5F
    #define DS18B20_TCONV_MS 375
#elif (DS18B20_RESOLUTION_BITS == 10)
    #define DS18B20_CONFIG_BYTE 0x3F
    #define DS18B20_TCONV_MS 188
#elif (DS18B20_RESOLUTION_BITS == 9)
    #define DS18B20_CONFIG_BYTE 0x1F
    #define DS18B20_TCONV_MS 94
#else
    #error Invalid DS18B20 resolution
#endif

#endif	// DEFAULTS_H
