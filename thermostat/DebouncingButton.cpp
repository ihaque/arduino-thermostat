#include "DebouncingButton.h"

void DebouncingButton::check_state() {
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

byte DebouncingButton::state() {
    check_state();
    return button_state;
}

bool DebouncingButton::was_pressed() {
    byte old_state = button_state;
    check_state();
    return (button_state == pressed_state && old_state != button_state);
}

void DebouncingButton::clear() {
    // To "reset" the button on a display refresh so we can repeat
    button_state = !button_state;
}

