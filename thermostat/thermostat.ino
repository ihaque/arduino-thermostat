#include <SoftwareSerial.h>
#include <EEPROM.h>

#include "defaults.h"
#include "pc_interface.h"

SoftwareSerial sLCD =  SoftwareSerial(0, CAN_BUS_LCD_TX); 
#define COMMAND 0xFE
#define CLEAR   0x01
#define LINE0   0x80
#define LINE1   0xC0


#include "OneWire.h"
OneWire ds(DS18B20_DQ);
byte DS18B20_addr[8];

class DebouncingButton
{
    private:
    byte last_button_state;
    byte button_state;
    byte pin;
    byte pressed_state;
    void check_state()
    {
        unsigned long last_debounce_time = 0;
        const unsigned long debounce_delay_ms = 5;
        byte current_state = digitalRead(pin);
        if (current_state != last_button_state) {
            last_debounce_time = millis();
        }

        if ((millis() - last_debounce_time) > debounce_delay_ms) {
            button_state = current_state;
        }
        last_button_state = current_state;
    }

    public:
    DebouncingButton(byte button_pin): pin(button_pin), pressed_state(0) {};
    byte state() {
        check_state();
        return button_state;
    }
    bool was_pressed() {
        byte old_state = button_state;
        check_state();
        return (button_state == pressed_state && old_state != button_state);
    }
    void clear() {
        // To "reset" the button on a display refresh so we can repeat
        button_state = !button_state;
    }
};

DebouncingButton down_button(DOWN);
DebouncingButton up_button(UP);

// TODO store error strings in flash to save RAM
void error_and_halt(const char* str) {
    Serial.print("error: ");
    Serial.println(str);
    
    clear_lcd();
    sLCD.print(str);
  
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

void initSD() {
    #ifdef _USE_SD_
    pinMode(CAN_BUS_SD_CS, OUTPUT);
    if (!_sdfat.begin(CAN_BUS_SD_CS)) {
      Serial.println("SD initialization failed!");
      return;
    }
    Serial.println("SD initialization success");
    #endif
    return;
}

void initLCD(unsigned int baud) {
    byte speed_control;
    switch (baud) {
      case 2400U: speed_control = 0x0B; break;
      case 4800U: speed_control = 0x0C; break;
      case 9600U: speed_control = 0x0D; break;
      case 14400U: speed_control = 0x0E; break;
      case 19200U: speed_control = 0x0F; break;
      case 38400U: speed_control = 0x10; break;
      default: baud = 9600U; speed_control = 0x0D; break;
    }

    sLCD.begin(9600U);
    sLCD.write(0x7C);
    sLCD.write(speed_control);
    delay(50); // Delay, or else LCD goes blank
    sLCD.begin(baud);
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
    initSD();
    initLCD(9600);
    clear_lcd();
    init_DS18B20(DS18B20_RESOLUTION_BITS);
}

void display_temp_slcd(int8_t integral, uint16_t fractional) 
{
    char line0[17];
    char line1[17];
    static char spinner = 'l';
    switch (spinner) {
      case 'l':
          spinner = '/'; break;
      case '/':
          spinner = '-'; break;
      case '-':
          spinner = '`'; break;
      case '`':
          spinner = 'l'; break;
    }
    sprintf(line0, "Temp: % 3d.%04u C", integral, fractional);
    sprintf(line1, "%c    Set: % 4d C",
            spinner, EEPROM.read(SETPOINT_EEPROM_ADDR));

    clear_lcd();
    sLCD.write(COMMAND);
    sLCD.write(LINE0);
    sLCD.print(line0);
    sLCD.write(COMMAND);
    sLCD.write(LINE1);
    sLCD.print(line1);
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

void clear_lcd(void)
{
    sLCD.write(COMMAND);
    sLCD.write(CLEAR);
}
