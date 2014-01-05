#ifndef _SerialLCD_h_
#define _SerialLCD_h_

#include <Arduino.h>
#include <SoftwareSerial.h>

class SerialLCD {
    private:
        static const byte COMMAND = 0xFE;
        static const byte CLEAR = 0x01;
        static const byte LINE0 = 0x80;
        static const byte LINE1 = 0xC0;
        SoftwareSerial port;
        unsigned baud_rate;
    public:
        SerialLCD(const byte pin): port(0, pin), baud_rate(9600) {};
        void initialize(unsigned new_baud);
        void clear(void);
        void writeln(const byte line, const char* text);
};
#endif
