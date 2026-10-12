#pragma once

#include "Particle.h"

#ifndef SI7021_CUSTOM
    #ifndef SI7021_TINY
        /**
         * Build device info functionality
         *
         * This adds `readDeviceInfo()` functionality and the corresponding
         * `serial` and `firmwareRevision` fields
         */
        #define SI7021_FEATURE_DEVICEINFO
        /**
         * Build Heater support
         *
         * Add internal heater control commands
         */
        #define SI7021_FEATURE_HEATER
        /**
         * Do CRC checks for each measurement
         */
        #define SI7021_FEATURE_CRC
    #endif
#endif


class Si7021 {
public:

#ifdef SI7021_FEATURE_DEVICEINFO
    /**
     * The device serial
     *
     * Contains the sensor serial number after a call to `readDeviceInfo()`
     * It consists of 8 bytes, for example:
     *  `45db524915b5ffff`
     */
    uint8_t serial[8];

    /**
     * The devices firmware revision
     *
     * This is one of the following:
     *
     * <pre>
     * * 0xff - firmware version 1.0
     * * 0x20 - firmware version 2.0
     * </pre>
     */
    uint8_t firmwareRevision = 0;

#endif

#ifdef SI7021_FEATURE_CRC
    /**
     * Indicates if the last Measurement's CRC was good
     *
     * This is the result of a CRC check on the data returned when a measurement
     * was done. It is only applicable for `readTemperature()` and
     * `readHumidity()`, and keeps its state until the next call of one of these.
     */
    bool wasLastMeasurementValid;
#endif

    Si7021();

    /**
     * Initialize the library and the sensor
     * @return success
     */
    bool begin(void);

    /**
     * Do a temperature measurement
     *
     * @return Temperature measured in degree Celsius
     */
    float readTemperature(void);

    /**
     * Get the temperature implicitly measured by the last humidity measurement
     *
     * Every humidity measurement implicitly measures the temperature too.
     * Instead of doing separate humidity and temperature measurements, one can
     * just measure the humidity once and get the internal temperature value
     * afterwards.
     *
     * @return Temperature measured in degree Celsius
     */
    float readLastTemperature(void);

    /**
     * Do a humidity measurement and read the humidity
     *
     * @return relative humidity in percent
     */
    float readHumidity(void);

    /**
     * Reset the sensor to it's default configuration
     *
     * This is automatically called by `begin()`, and resets
     * the sensors internal configuration registers.
     *
     * <pre>
     *  * heater off
     *  * heater current: 3.09mA
     *  * resolution: 12bit RH, 14bit temp
     * </pre>
     *
     * @return true on success
     */
    bool reset(void);

#ifdef SI7021_FEATURE_DEVICEINFO
    /**
     * Read device info
     *
     * Read out some sensor information: the serial number, and the firmware
     * revision. Those are accessible via the public properties firmwareRevision
     * and serial afterwards.
     */
    void readDeviceInfo(void);
#endif

#ifdef SI7021_FEATURE_HEATER
    /**
     * Turn the integrated heater on or off
     *
     * @param state desired state (false == off, true == on)
     */
    void heater(bool state);

    /**
     * Set the desired heater power
     *
     * Configure the power level of the integrated heater. This can be set to
     * any value between 0 and 15 (0x0 - 0xf). Lower values mean less current
     * drawn and less heating.
     *
     * This does not automatically turn the heater on! Use Si7021::heater() for
     * changing the heaters state.
     *
     * Examples:
     *
     * <pre>
     *      power       typical current draw (mA)
     *      0x0         3.09
     *      0x1         9.18
     *      0x2         15.24
     *      ...         ...
     *      0x4         27.39
     *      ...         ...
     *      0x8         51.69
     *      ...         ...
     *      0xf         94.20
     * </pre>
     *
     * @param desired Desired power level
     */
    void setHeaterPower(uint8_t desired);
#endif


private:
    int8_t i2caddr;

    uint8_t sendBytes(uint8_t *data, int length, bool endTransmission = false);
    bool readBytes(uint8_t *buffer, int length);
    bool cmd(uint8_t cmd, uint8_t *buffer, uint8_t expected, int duration);
    uint8_t crc8(uint8_t *data, uint8_t length);
};
