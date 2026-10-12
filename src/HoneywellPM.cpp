#include "HoneywellPM.h"

HoneywellPM::Result HoneywellPM::start() {
    uint16_t unused25 = 0, unused10 = 0;
    Result result = command(0x20, false, unused25, unused10); // Stop auto-send.
    if (result != Result::OK) return result;
    return command(0x01, false, unused25, unused10); // Start measurements.
}

HoneywellPM::Result HoneywellPM::read(uint16_t& pm25, uint16_t& pm10) {
    return command(0x04, true, pm25, pm10);
}

HoneywellPM::Result HoneywellPM::command(uint8_t code, bool measurement,
                                        uint16_t& pm25, uint16_t& pm10) {
    // Bound draining even if an unexpected sender continuously produces bytes.
    for (unsigned i = 0; i < 256 && serial_.available(); ++i) serial_.read();
    const uint8_t packet[] = {0x68, 0x01, code,
        static_cast<uint8_t>(0u - (0x68u + 0x01u + code))};
    if (serial_.write(packet, sizeof(packet)) != sizeof(packet)) return Result::TIMEOUT;

    uint8_t frame[32];
    size_t count = 0, needed = 0;
    bool invalid = false;
    const uint32_t started = millis();
    // One deadline for the entire transaction, including partial frames/noise.
    while (static_cast<uint32_t>(millis() - started) < 250) {
        if (!serial_.available()) {
            delay(1);
            continue;
        }
        const uint8_t byte = static_cast<uint8_t>(serial_.read());
        if (count == 0) {
            if (byte != 0x40 && byte != 0x42 && byte != 0xA5 && byte != 0x96) continue;
            frame[count++] = byte;
            continue;
        }
        frame[count++] = byte;
        if (count == 2) {
            if ((frame[0] == 0xA5 && byte == 0xA5) ||
                (frame[0] == 0x96 && byte == 0x96)) {
                if (frame[0] == 0x96) return Result::NACK;
                if (!measurement) return Result::OK;
                count = 0; // A read requires data, not just an ACK.
                needed = 0;
                continue;
            }
            if (frame[0] == 0x40 && byte == 0x05) needed = 8;
            else if (frame[0] == 0x42 && byte == 0x4D) needed = 32;
            else {
                invalid = true;
                count = 0;
                needed = 0;
                // Keep a possible new header after a truncated/noisy prefix.
                if (byte == 0x40 || byte == 0x42 || byte == 0xA5 || byte == 0x96)
                    frame[count++] = byte;
            }
        }
        if (!needed || count != needed) continue;

        if (needed == 8) {
            uint8_t sum = 0;
            for (size_t i = 0; i < 8; ++i) sum += frame[i];
            if (frame[2] == 0x04 && sum == 0 && measurement) {
                pm25 = (static_cast<uint16_t>(frame[3]) << 8) | frame[4];
                pm10 = (static_cast<uint16_t>(frame[5]) << 8) | frame[6];
                return Result::OK;
            }
            if (frame[2] != 0x04 || sum != 0) invalid = true;
        } else {
            // Auto-send may overlap the command that disables it. Consume the
            // entire frame so its payload cannot masquerade as an ACK.
            uint16_t sum = 0;
            for (size_t i = 0; i < 30; ++i) sum += frame[i];
            const uint16_t checksum = (static_cast<uint16_t>(frame[30]) << 8) | frame[31];
            if (frame[2] != 0 || frame[3] != 28 || sum != checksum) invalid = true;
        }
        count = 0;
        needed = 0;
    }
    return invalid ? Result::INVALID_FRAME : Result::TIMEOUT;
}

const char* HoneywellPM::status(Result result) {
    switch (result) {
        case Result::OK: return "ok";
        case Result::TIMEOUT: return "timeout/short response";
        case Result::NACK: return "negative acknowledgement";
        case Result::INVALID_FRAME: return "invalid frame/checksum";
    }
    return "unknown";
}
