/* Si7021 library by Stefan Linke
 */

#include "Si7021.h"



#define SI7021_DEFAULT_ADDRESS           0x40
#define SI7021_DEFAULT_SETTINGS          0x3a

// I2C commands
#define SI7021_CMD_MEASRH_HOLD           0xE5
#define SI7021_CMD_MEASRH_NOHOLD         0xF5
#define SI7021_CMD_MEASTEMP_HOLD         0xE3
#define SI7021_CMD_MEASTEMP_NOHOLD       0xF3
#define SI7021_CMD_READPREVTEMP          0xE0
#define SI7021_CMD_RESET                 0xFE
#define SI7021_CMD_WRITERHT_REG          0xE6
#define SI7021_CMD_READRHT_REG           0xE7
#define SI7021_CMD_WRITEHEATER_REG       0x51
#define SI7021_CMD_READHEATER_REG        0x11
// those 2 byte commands are endianess-swapped to be sent bytewise
#define SI7021_CMD_ID1                   0x0FFA
#define SI7021_CMD_ID2                   0xC9FC
#define SI7021_CMD_FIRMVERS              0xB884

// configuration
#define SI7021_CFGBIT_RES0     0
#define SI7021_CFGBIT_HTRE     2
#define SI7021_CFGBIT_VDDS     6
#define SI7021_CFGBIT_RES1     7

#define SI7021_HEATER_MASK     0x0f



Si7021::Si7021(void) {
    this->i2caddr = SI7021_DEFAULT_ADDRESS;
}

bool Si7021::begin(void) {
    uint8_t settings;

    Wire.begin();

    if (!reset()) {
        return false;
    }

    if (!cmd(SI7021_CMD_READRHT_REG, &settings, 1, 0) || settings != SI7021_DEFAULT_SETTINGS) {
        // device is not running with default configuration
        // probably sth broke
        return false;
    }

#ifdef SI7021_FEATURE_CRC
    wasLastMeasurementValid = true;
#endif

    return true;
}

float Si7021::readHumidity(void) {
    uint8_t data[3];
    float humidity;

    const bool received = cmd(SI7021_CMD_MEASRH_NOHOLD, data, 3, 25);
#ifdef SI7021_FEATURE_CRC
    wasLastMeasurementValid = received && data[2] == crc8(data, 2);
    if (!wasLastMeasurementValid) return NAN;
#else
    if (!received) return NAN;
#endif
    humidity = ((float) (((uint16_t) data[0] << 8) | data[1]) * 125) / 65536 - 6;

    // clamp values to 0-100% range
    // it is in some cases possible that the values are outside of this range, according to spec
    if (humidity < 0) {
        humidity = 0.0;
    } else if (humidity > 100.0) {
        humidity = 100.0;
    }

#ifdef SI7021_FEATURE_CRC
    wasLastMeasurementValid = data[2] == crc8(data, 2);
#endif

    return humidity;
}

float Si7021::readTemperature(void) {
    uint8_t data[3];
    float temperature;

    const bool received = cmd(SI7021_CMD_MEASTEMP_NOHOLD, data, 3, 25);
#ifdef SI7021_FEATURE_CRC
    wasLastMeasurementValid = received && data[2] == crc8(data, 2);
    if (!wasLastMeasurementValid) return NAN;
#else
    if (!received) return NAN;
#endif
    temperature = ((float) (((uint16_t) data[0] << 8) | data[1]) * 175.72) / 65536 - 46.85;

#ifdef SI7021_FEATURE_CRC
    wasLastMeasurementValid = data[2] == crc8(data, 2);
#endif

    return temperature;
}

float Si7021::readLastTemperature(void) {
    uint8_t data[2];
    float temperature;

    if (!cmd(SI7021_CMD_READPREVTEMP, data, 2, 0)) return NAN;
    temperature = ((float) (((uint16_t) data[0] << 8) | data[1]) * 175.72) / 65536 - 46.85;
    return temperature;
}

bool Si7021::reset(void) {
    uint8_t cmd = SI7021_CMD_RESET;
    uint8_t error = sendBytes(&cmd, 1, true);
    delay(50);

    return error == 0;
}

#ifdef SI7021_FEATURE_DEVICEINFO

void Si7021::readDeviceInfo(void) {
    uint16_t command = SI7021_CMD_ID1;

    // serial number part 1
    sendBytes((uint8_t*) &command, 2, true);

    Wire.requestFrom(i2caddr, 8);
    serial[0] = Wire.read();
    Wire.read();
    serial[1] = Wire.read();
    Wire.read();
    serial[2] = Wire.read();
    Wire.read();
    serial[3] = Wire.read();
    Wire.read();

    // serial number part 2
    command = SI7021_CMD_ID2;
    sendBytes((uint8_t*) &command, 2, true);

    Wire.requestFrom(i2caddr, 8);
    serial[4] = Wire.read();
    Wire.read();
    serial[5] = Wire.read();
    Wire.read();
    serial[6] = Wire.read();
    Wire.read();
    serial[7] = Wire.read();
    Wire.read();

    // firmware revision
    command = SI7021_CMD_FIRMVERS;
    sendBytes((uint8_t*) &command, 2, true);

    Wire.requestFrom(i2caddr, 1);
    firmwareRevision = Wire.read();
}

#endif

#ifdef SI7021_FEATURE_HEATER

void Si7021::heater(bool state) {
    uint8_t config;

    cmd(SI7021_CMD_READRHT_REG, &config, 1, 0);

    if (state) {
        config |= 1 << SI7021_CFGBIT_HTRE;
    } else {
        config &= ~(1 << SI7021_CFGBIT_HTRE);
    }

    uint8_t writeSequence[] = {SI7021_CMD_WRITERHT_REG, config};
    sendBytes(writeSequence, 2, true);
}

void Si7021::setHeaterPower(uint8_t desired) {
    uint8_t power;

    cmd(SI7021_CMD_READHEATER_REG, &power, 1, 0);

    // preserve reserved bits
    power &= ~((uint8_t) SI7021_HEATER_MASK);
    power |= desired & SI7021_HEATER_MASK;

    uint8_t writeSequence[] = {SI7021_CMD_WRITEHEATER_REG, power};
    sendBytes(writeSequence, 2, true);
}

#endif

uint8_t Si7021::sendBytes(uint8_t *data, int length, bool endTransmission) {
    Wire.beginTransmission(i2caddr);
    for(int i = 0; i < length; ++i) {
        Wire.write(data[i]);
    }
    return Wire.endTransmission(endTransmission);
}

bool Si7021::readBytes(uint8_t *buffer, int length) {
    if (Wire.requestFrom(i2caddr, length) != static_cast<size_t>(length)) return false;
    for(int i = 0; i < length; ++i) {
        buffer[i] = Wire.read();
    }
    return true;
}

bool Si7021::cmd(uint8_t cmd, uint8_t *buffer, uint8_t expected, int duration) {
    uint8_t error = sendBytes(&cmd, 1);
    if (error != 0) return false;
    delay(duration);
    if (expected > 0 && buffer != NULL) {
        return readBytes(buffer, expected);
    }
    return error == 0;
}

#ifdef SI7021_FEATURE_CRC

uint8_t Si7021::crc8(uint8_t *data, uint8_t length)
{
    uint8_t crc = 0;
    int8_t i, j;

    for (i = 0; i < length; ++i) {
        crc ^= data[i];
        for (j = 8; j > 0; --j) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x131;
            else
                crc <<= 1;
        }
    }

    return crc;
}

#endif
