#include "HoneywellPM.h"
#include <cassert>
#include <deque>
#include <cstdio>
uint32_t clockMs = 0;
TwoWire Wire;
using Result = HoneywellPM::Result;
class FakeSerial : public Stream {
public:
 std::deque<uint8_t> input;
 std::vector<uint8_t> response;
 std::vector<std::vector<uint8_t>> commands;
 bool nack = false, silent = false;
 int available() override { return input.size(); }
 int read() override { auto b = input.front(); input.pop_front(); return b; }
 size_t write(const uint8_t* bytes, size_t n) override {
   commands.emplace_back(bytes, bytes+n);
   uint8_t sum=0; for(size_t i=0;i<n;i++) sum+=bytes[i];
   assert(n == 4 && bytes[0] == 0x68 && bytes[1] == 1 && sum == 0);
   if (silent) return n;
   if (nack) { input={0x96,0x96}; return n; }
   if (bytes[2] != 4) input={0xA5,0xA5};
   else input.insert(input.end(),response.begin(),response.end());
   return n;
 }
};
std::vector<uint8_t> reading() { return {0x40,0x05,0x04,0x00,0x30,0x00,0x31,0x56}; }
int main() {
 FakeSerial serial; HoneywellPM pm(serial); uint16_t pm25=99,pm10=98;
 assert(pm.start()==Result::OK);
 assert(serial.commands[0][2]==0x20 && serial.commands[1][2]==0x01);
 serial.response=reading(); assert(pm.read(pm25,pm10)==Result::OK && pm25==48 && pm10==49);
 serial.response.back()^=1; pm25=99;pm10=98;
 assert(pm.read(pm25,pm10)==Result::INVALID_FRAME && pm25==99 && pm10==98);
 serial.response={0x40,0x05,0x04}; auto before=clockMs;
 assert(pm.read(pm25,pm10)==Result::TIMEOUT && clockMs-before<=252);
 serial.nack=true; assert(pm.read(pm25,pm10)==Result::NACK); serial.nack=false;
 serial.response={0xA5,0xA5}; assert(pm.read(pm25,pm10)==Result::TIMEOUT);
 serial.response={0xff,0x40,0x40}; auto valid=reading();
 serial.response.insert(serial.response.end(),valid.begin()+1,valid.end());
 assert(pm.read(pm25,pm10)==Result::OK);
 serial.response=reading(); serial.response.back()^=1;
 serial.response.insert(serial.response.end(),valid.begin(),valid.end());
 assert(pm.read(pm25,pm10)==Result::OK);
 // Valid unsolicited auto-send frame, including ACK-like payload bytes.
 serial.response=std::vector<uint8_t>(32,0); serial.response[0]=0x42;serial.response[1]=0x4d;serial.response[3]=28;
 serial.response[4]=0xa5;serial.response[5]=0xa5;
 uint16_t sum=0;for(int i=0;i<30;i++) sum+=serial.response[i];
 serial.response[30]=sum>>8;serial.response[31]=sum&255;
 serial.response.insert(serial.response.end(),valid.begin(),valid.end());
 assert(pm.read(pm25,pm10)==Result::OK && pm25==48 && pm10==49);
 serial.silent=true; before=clockMs;assert(pm.read(pm25,pm10)==Result::TIMEOUT && clockMs-before<=252);
 // Transaction deadline is safe across millis() rollover.
 clockMs=0xfffffff0;before=clockMs;
 assert(pm.read(pm25,pm10)==Result::TIMEOUT && uint32_t(clockMs-before)<=252);
 puts("Honeywell: start commands, valid data, bad checksum, partial/missing responses, NACK, ACK-only read, noise resync, auto-send overlap, rollover passed");
}
