#include <SoftwareSerial.h>
#include <EEPROM.h>

#include "defaults.h"
#include "pc_interface.h"
#include "SerialLCD.h"
#include "OneWire.h"
#include "DebouncingButton.h"

SerialLCD sLCD(CAN_BUS_LCD_TX);
OneWire ds(DS18B20_DQ);
byte DS18B20_addr[8];
DebouncingButton down_button(DOWN);
DebouncingButton up_button(UP);

void error_and_halt(const char* str) {
    Serial.print("error: ");
    Serial.println(str);
    
    sLCD.clear();
    sLCD.writeln(0, str);
  
    while(1);
}

void initJoy(void) {
    pinMode(UP, INPUT_PULLUP);
    pinMode(DOWN, INPUT_PULLUP);
    pinMode(LEFT, INPUT_PULLUP);
    pinMode(RIGHT, INPUT_PULLUP);
    pinMode(CLICK, INPUT_PULLUP);
    return;
}

void init_DS18B20(uint8_t resolution) {
    // This code assumes there is exactly one 1-wire device on the bus
    // and it is a DS18B20
    if (!ds.search(DS18B20_addr)) {
        ds.reset_search();
        error_and_halt("No 1wire addrs!");
        return;
    }
    if (OneWire::crc8(DS18B20_addr, 7) != DS18B20_addr[7]) {
        error_and_halt("Invalid CRC");
        return;
    }

    if (DS18B20_addr[0] != 0x28) {
        error_and_halt("Unknown device");
        return;
    }
    ds.reset();
    ds.select(DS18B20_addr);
    ds.write(0x4E); // Write scratchpad
    ds.write(0x00); // 0 -> Th
    ds.write(0x00); // 0 -> Tl
    ds.write(DS18B20_CONFIG_BYTE); // Configure resolution
    ds.reset();
}

void convert_temperature(const uint8_t lsb, const uint8_t msb,
                         int8_t& integral, uint16_t& fractional,
                         const uint8_t resolution)
{
    // LSB: 2^3 ... 2^-4
    // MSB: S S S S S 2^6 2^5 2^4
    // Knock off the appropriate bits in the LSB depending on res
    const uint8_t mask = (0xFU >> (12 - resolution)) << (12 - resolution);
    integral = ((int8_t) (msb << 4)) | ((int8_t) (lsb >> 4));

    uint8_t binary_fractional;
    if (integral < 0) {
        binary_fractional = (~lsb + 1) & mask;
    } else {
        binary_fractional = lsb & mask;
    }
    fractional = 0;
    if (binary_fractional & 0x1) fractional += 625;
    if (binary_fractional & 0x2) fractional += 1250;
    if (binary_fractional & 0x4) fractional += 2500;
    if (binary_fractional & 0x8) fractional += 5000;

    return;
}

void setup() 
{
    Serial.begin(115200);
    initJoy();
    sLCD.initialize(9600);
    init_DS18B20(DS18B20_RESOLUTION_BITS);
}

void display_temp_slcd(int8_t integral, uint16_t fractional) 
{
    static int8_t last_setpoint = -1;
    static int8_t last_integral = -127;
    static int8_t last_rounded_fractional = -1;

    char line[17];

    const int8_t setpoint = EEPROM.read(SETPOINT_EEPROM_ADDR);
    const uint16_t epsilon = fractional % 1000;
    fractional /= 1000;
    if (epsilon >= 500) fractional++;
    if (fractional == 10) {
        fractional = 0;
        integral++;
    }

    if (integral != last_integral || fractional != last_rounded_fractional) {
        sprintf(line, "  Temp: % 4d.%01u C", integral, fractional);
        sLCD.writeln(0, line);
        last_integral = integral;
        last_rounded_fractional = fractional;
    }
    if (setpoint != last_setpoint) {
        sprintf(line, "   Set: % 4d.0 C", EEPROM.read(SETPOINT_EEPROM_ADDR));
        sLCD.writeln(1, line);
        last_setpoint = setpoint;
    }
}

void delay_with_input(unsigned long delay_ms) {
    unsigned long delay_start = millis();

    int8_t setpoint = EEPROM.read(SETPOINT_EEPROM_ADDR);
    if (setpoint > 50) setpoint = 50;
    if (setpoint < 0) setpoint = 0;

    while ((millis() - delay_start) < delay_ms) {
        if (up_button.was_pressed() && setpoint < 50) {
            setpoint++;
        } else if (down_button.was_pressed() && setpoint > 0) {
            setpoint--;
        }
    }
    if (setpoint != EEPROM.read(SETPOINT_EEPROM_ADDR)) {
        EEPROM.write(SETPOINT_EEPROM_ADDR, setpoint);
    }
    return;
}

void loop(void) 
{
    ds.reset();
    ds.select(DS18B20_addr);
    ds.write(0x44); // start temperature conversion
    delay_with_input(DS18B20_TCONV_MS);
    
    ds.reset();
    ds.select(DS18B20_addr);
    ds.write(0xBE);
    uint8_t t_lsb = ds.read();
    uint8_t t_msb = ds.read();
    ds.reset();

    int8_t integral;
    uint16_t fractional;
    convert_temperature(t_lsb, t_msb, integral, fractional,
                        DS18B20_RESOLUTION_BITS);
    
    display_temp_slcd(integral, fractional);
    upload_temperature_data(integral, fractional,
                            EEPROM.read(SETPOINT_EEPROM_ADDR));
    down_button.clear();
    up_button.clear();
};
