#include "SerialLCD.h"

void SerialLCD::initialize(unsigned new_baud) {
    byte speed_control;
    switch (new_baud) {
      case 2400U: speed_control = 0x0B; break;
      case 4800U: speed_control = 0x0C; break;
      case 9600U: speed_control = 0x0D; break;
      case 14400U: speed_control = 0x0E; break;
      case 19200U: speed_control = 0x0F; break;
      case 38400U: speed_control = 0x10; break;
      default: new_baud = 9600U; speed_control = 0x0D; break;
    }

    port.begin(baud_rate);
    port.write(0x7C);
    port.write(speed_control);
    delay(50); // Delay, or else LCD goes blank
    port.begin(new_baud);
    baud_rate = new_baud;
    clear();
    return;
}
void SerialLCD::clear(void) {
    port.write(COMMAND);
    port.write(CLEAR);
}
void SerialLCD::writeln(const byte line, const char* text) {
    port.write(COMMAND);
    if (line == 0) port.write(LINE0);
    else port.write(LINE1);
    port.print(text);
}
