#ifndef _DebouncingButton_h_
#define _DebouncingButton_h_

#include <Arduino.h>

class DebouncingButton {
    private:
    byte last_button_state;
    byte button_state;
    byte pin;
    byte pressed_state;
    void check_state();

    public:
    DebouncingButton(byte button_pin): pin(button_pin), pressed_state(0) {};
    byte state();
    bool was_pressed();
    void clear();
};
#endif
