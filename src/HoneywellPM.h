#pragma once
#include "Particle.h"

// HPMA115S0 standard sensor; caller starts UART at 9600 baud, 8N1.
class HoneywellPM {
public:
    enum class Result { OK, TIMEOUT, NACK, INVALID_FRAME };
    explicit HoneywellPM(Stream& serial) : serial_(serial) {}
    Result start();
    Result read(uint16_t& pm25, uint16_t& pm10);
    static const char* status(Result result);
private:
    Result command(uint8_t code, bool measurement, uint16_t& pm25, uint16_t& pm10);
    Stream& serial_;
};
