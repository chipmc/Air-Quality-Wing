#include "Si7021.h"
#include "SparkFunCCS811.h"
#include <cassert>
#include <cmath>
#include <cstdio>
TwoWire Wire;
uint32_t clockMs=0;
bool appStartSeen=false;
unsigned appStartDelay=0;
uint8_t observeTransmission(const std::vector<uint8_t>& tx) {
 assert(!tx.empty());
 if(appStartSeen) assert(appStartDelay>=1); // Before ANY subsequent I2C command.
 if(tx[0]==CSS811_APP_START) appStartSeen=true;
 return 0;
}
size_t registerResponse(size_t n) {
 assert(n==1 && !Wire.tx.empty());
 const auto reg=Wire.tx[0];
 Wire.rx={reg==CSS811_HW_ID ? 0x81 : reg==CSS811_STATUS ? 0x90 : 0x10};
 Wire.rxCount=1;
 return 1;
}
void observeDelay(unsigned ms) { if(appStartSeen) appStartDelay+=ms; }
uint8_t crc8(uint8_t a,uint8_t b) { uint8_t crc=0;for(uint8_t v:{a,b}){crc^=v;for(int i=0;i<8;i++)crc=(crc&0x80)?(crc<<1)^0x31:crc<<1;}return crc; }
int main(){
 CCS811 ccs(0x5a);ccs.beginCore(Wire);
 uint8_t out[4]={1,2,3,4};
 Wire.rxCount=0;Wire.txStatus=0;
 assert(ccs.multiReadRegister(CSS811_ALG_RESULT_DATA,out,4)==CCS811Core::CCS811_Stat_I2C_ERROR);
 Wire.rxCount=2;Wire.rx={0,1};
 assert(ccs.multiReadRegister(CSS811_ALG_RESULT_DATA,out,4)==CCS811Core::CCS811_Stat_I2C_ERROR);
 Wire.rxCount=0;assert(ccs.readRegister(CSS811_STATUS,out)==CCS811Core::CCS811_Stat_I2C_ERROR);
 Wire.rxCount=4;Wire.rx={0x02,0x6c,0,0x55};
 assert(ccs.readAlgorithmResults()==CCS811Core::CCS811_Stat_SUCCESS && ccs.getCO2()==620 && ccs.getTVOC()==85);
 Si7021 si;Wire.rxCount=3;Wire.rx={0x68,0x3a,crc8(0x68,0x3a)};
 Wire.txStatus=4;assert(std::isnan(si.readTemperature()) && !si.wasLastMeasurementValid);
 Wire.txStatus=0;Wire.rxCount=2;assert(std::isnan(si.readHumidity()) && !si.wasLastMeasurementValid);
 Wire.rxCount=3;Wire.rx={0x68,0x3a,crc8(0x68,0x3a)};
 assert(std::isfinite(si.readTemperature()) && si.wasLastMeasurementValid);
 Wire.rx[2]^=1;assert(std::isnan(si.readTemperature()) && !si.wasLastMeasurementValid);
 Wire.rxCount=0;assert(!si.begin());
 Wire.endHook=observeTransmission;Wire.requestHook=registerResponse;delayObserver()=observeDelay;
 assert(ccs.beginWithStatus()==CCS811Core::CCS811_Stat_SUCCESS);
 assert(appStartSeen && appStartDelay==1);
 puts("Published library regressions: short/missing reads, failed commands, valid values, CRC failures, initialization failure and APP_START delay passed");
}
