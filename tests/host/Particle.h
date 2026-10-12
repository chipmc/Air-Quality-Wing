#pragma once
#include <cstdint>
#include <cstddef>
#include <cmath>
#include <vector>
#include <algorithm>
using std::size_t;
using DelayObserver = void (*)(unsigned);
inline DelayObserver& delayObserver() { static DelayObserver observer = nullptr; return observer; }
inline void delay(unsigned ms) { if (delayObserver()) delayObserver()(ms); }
inline void delayMicroseconds(unsigned) {}
class TwoWire {
public:
 int txStatus = 0; size_t rxCount = 0; std::vector<int> rx; size_t pos = 0;
 std::vector<uint8_t> tx;
 uint8_t (*endHook)(const std::vector<uint8_t>&) = nullptr;
 size_t (*requestHook)(size_t) = nullptr;
 void begin() {} void beginTransmission(uint8_t) { tx.clear(); }
 size_t write(uint8_t b) { tx.push_back(b); return 1; }
 size_t write(const uint8_t* bytes, size_t n) { tx.insert(tx.end(), bytes, bytes+n); return n; }
 uint8_t endTransmission(bool = true) { return endHook ? endHook(tx) : txStatus; }
 size_t requestFrom(uint8_t, size_t n) { pos = 0; return requestHook ? requestHook(n) : std::min(n, rxCount); }
 int available() { return static_cast<int>(rxCount - pos); }
 int read() { return pos < rxCount ? rx[pos++] : -1; }
};
extern TwoWire Wire;

using byte = uint8_t;
extern uint32_t clockMs;
inline uint32_t millis() { return clockMs++; }
class Stream {
public:
 virtual ~Stream() = default;
 virtual int available() = 0;
 virtual int read() = 0;
 virtual size_t write(const uint8_t*, size_t) = 0;
};
