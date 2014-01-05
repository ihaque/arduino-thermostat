#include <Arduino.h>

void upload_temperature_data(int8_t integral, uint16_t fractional, int8_t setpoint)
{
    // {"temperature": -123.4567, "setpoint": -123}\n
    char json_buffer[48];
    sprintf(json_buffer, "{\"temperature\": %d.%04u, \"setpoint\": %d}\n",
            integral, fractional, setpoint);
    Serial.print(json_buffer);
    Serial.flush();
}
