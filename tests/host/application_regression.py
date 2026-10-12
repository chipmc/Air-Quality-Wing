"""Compile actual application helpers with focused GPIO/time/CCS811 fakes."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'src/Air-Quality-Wing.cpp').read_text()

def function(signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

assert 'initializeControlPins();' in function('void setup(')
assert function('void setup(').split('{', 1)[1].lstrip().startswith('initializeUsbSerial();')
assert '#define ENABLE_USB_SERIAL_WAIT true' in source
assert '#define ENABLE_PUBLISH true' in source
assert 'reportDue(now)' in function('void loop(')
report = function('void report(')
rssi_start = report.index('const int32_t rssi')
rssi_end = report.index('json.endObject()', rssi_start)
rssi_function = 'void emitRssi() {\n' + report[rssi_start:rssi_end] + '}\n'

prefix = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdarg>
#include <string>
#include <vector>
constexpr int D5=5,D6=6,OUTPUT=1,HIGH=1,LOW=0;
uint32_t clockMs=100;
uint32_t millis(){return clockMs;}
constexpr bool usbSerialWaitEnabled=TEST_USB_WAIT_ENABLED;
struct FakeUsbSerial {
 unsigned baud=0,checks=0;
 uint32_t beganAt=0,connectAfter=0xffffffff;
 void begin(unsigned speed){baud=speed;beganAt=clockMs;}
 bool isConnected(){++checks;return uint32_t(clockMs-beganAt)>=connectAfter;}
} Serial;
int mode[7]={}, level[7]={};
std::vector<std::string> gpioCalls;
unsigned waited=0;
void pinMode(int pin,int value){mode[pin]=value;level[pin]=LOW;gpioCalls.push_back("mode"+std::to_string(pin));}
void digitalWrite(int pin,int value){assert(mode[pin]==OUTPUT);level[pin]=value;gpioCalls.push_back("write"+std::to_string(pin)+"="+std::to_string(value));}
void delay(unsigned ms){waited+=ms;clockMs+=ms;}
constexpr uint32_t reportInterval=60000;
uint32_t pmPowerTime=0,pmStartTime=0,lastReport=0;
bool firstReport=true,pmStarted=false;
constexpr int CSS811_STATUS=0,CSS811_ERROR_ID=0xe0;
struct CCS811Core {enum CCS811_Status_e {CCS811_Stat_SUCCESS,CCS811_Stat_I2C_ERROR};};
struct FakeCcs {
 uint8_t status=0x89,errorId=0x10;
 bool errorReadFails=false,statusReadFails=false;
 unsigned errorReads=0,measurementReads=0;
 CCS811Core::CCS811_Status_e readRegister(int reg,uint8_t* out){
  if(reg==CSS811_STATUS){if(statusReadFails)return CCS811Core::CCS811_Stat_I2C_ERROR;*out=status;return CCS811Core::CCS811_Stat_SUCCESS;}
  assert(reg==CSS811_ERROR_ID);++errorReads;
  if(errorReadFails)return CCS811Core::CCS811_Stat_I2C_ERROR;
  *out=errorId;status&=~1;return CCS811Core::CCS811_Stat_SUCCESS;
 }
 CCS811Core::CCS811_Status_e readAlgorithmResults(){++measurementReads;return CCS811Core::CCS811_Stat_SUCCESS;}
 uint16_t getCO2(){return 620;} uint16_t getTVOC(){return 85;}
} ccs811;
struct Logger {
 std::string last;
 std::vector<std::string> infos;
 std::vector<std::string> warnings;
 void info(const char* format,...){char buf[160];va_list ap;va_start(ap,format);vsnprintf(buf,sizeof(buf),format,ap);va_end(ap);infos.push_back(buf);}
 void warn(const char* format,...){char buf[160];va_list ap;va_start(ap,format);vsnprintf(buf,sizeof(buf),format,ap);va_end(ap);last=buf;warnings.push_back(buf);}
} Log;
bool ccsReady=true,vocValid=true,vocErrorLogged=false;
uint16_t eco2=0,tvoc=0;uint32_t vocTime=0;
struct FakeWifi {bool connected=false;int32_t signal=0;bool ready(){return connected;}int32_t RSSI(){return signal;}} WiFi;
struct FakeJson {bool isNull=true;int32_t number=0;void name(const char*){} void value(int32_t n){isNull=false;number=n;}void nullValue(){isNull=true;}} json;
'''
tests = r'''
int main(){
 Serial=FakeUsbSerial{};clockMs=100;waited=0;initializeUsbSerial();
 assert(Serial.baud==115200);
 if(usbSerialWaitEnabled){
  assert(waited==10000 && clockMs==10100); // No monitor: finite timeout.
  Serial=FakeUsbSerial{};Serial.connectAfter=0;waited=0;
  initializeUsbSerial();assert(waited==0); // Already connected.
  Serial=FakeUsbSerial{};Serial.connectAfter=250;waited=0;
  initializeUsbSerial();assert(waited==250); // Connect during the wait.
  Serial=FakeUsbSerial{};clockMs=0xfffffff0;waited=0;
  initializeUsbSerial();assert(waited==10000); // Timeout across rollover.
 }else assert(waited==0 && Serial.checks==0); // Production still initializes USB.
 printf("USB serial: wait enabled=%d, baud/timeout/connection/rollover checks passed\n",usbSerialWaitEnabled);
 clockMs=100;waited=0;
 initializeControlPins();
 assert((gpioCalls==std::vector<std::string>{"mode5","write5=1","mode6","write6=0"}));
 assert(mode[D5]==OUTPUT && level[D5]==HIGH && mode[D6]==OUTPUT && level[D6]==LOW);
 assert(pmPowerTime==100 && waited>=20); // Settle after the possible D5 LOW pulse.
 pmStarted=true;pmPowerTime=100;pmStartTime=6350;
 assert(!reportDue(12100)); // Old fixed 12-second schedule fired too early.
 assert(!reportDue(12349));assert(reportDue(12350));
 pmStarted=false;assert(!reportDue(12099));assert(reportDue(12100)); // Missing PM cannot block diagnostics.
 firstReport=false;lastReport=12350;
 assert(!reportDue(72349));assert(reportDue(72350));
 firstReport=true;pmStarted=true;pmPowerTime=0xffffe000;pmStartTime=pmPowerTime+6250;
 assert(!reportDue(uint32_t(pmStartTime+5999)));assert(reportDue(uint32_t(pmStartTime+6000)));
 readVoc();assert(!vocValid && ccs811.errorReads==1 && ccs811.measurementReads==0);
 assert(Log.warnings[Log.warnings.size()-2]=="CCS811 STATUS=0x89 DATA_READY=1 ERROR=1 APP_VALID=0 FW_MODE=1");
 assert(Log.last=="CCS811 ERROR_ID=0x10");
 const auto warningCount=Log.warnings.size();
 readVoc();assert(vocValid && eco2==620 && tvoc==85 && ccs811.measurementReads==1);
 assert(Log.warnings.size()==warningCount && Log.infos.empty());
 assert(ccs811.errorReads==1); // No ERROR_ID read when ERROR is clear.
 ccs811.status=0x90;readVoc();
 assert(Log.warnings.size()==warningCount && Log.infos.empty());
 assert(ccs811.measurementReads==1 && ccs811.errorReads==1);
 ccs811.status=0x98;
 for(unsigned i=0;i<10;++i)readVoc(); // Normal one-second polls stay quiet.
 assert(vocValid && ccs811.measurementReads==11 && ccs811.errorReads==1);
 assert(Log.warnings.size()==warningCount && Log.infos.empty());
 ccs811.status=0x10;readVoc();assert(!vocValid);
 assert(Log.last=="CCS811 not in application mode" && Log.infos.empty());
 const auto logCount=Log.infos.size();ccs811.statusReadFails=true;
 readVoc();assert(!vocValid && Log.infos.size()==logCount); // Never log a fabricated STATUS.
 ccs811.statusReadFails=false;
 ccs811.status=0x89;ccs811.errorReadFails=true;
 readVoc();assert(!vocValid && Log.last=="CCS811 ERROR_ID read failed");
 assert(ccs811.status & 1); // Failed read cannot be treated as clearing ERROR.
 WiFi.connected=false;WiFi.signal=-58;emitRssi();assert(json.isNull);
 WiFi.connected=true;WiFi.signal=0;emitRssi();assert(json.isNull);
 WiFi.signal=1;emitRssi();assert(json.isNull);
 WiFi.signal=-58;emitRssi();assert(!json.isNull && json.number==-58);
 puts("Application: GPIO ordering/states/settling, first-report warmup, missing PM, cadence, rollover, CCS811 STATUS flags/failed reads/ERROR_ID handling and RSSI validation passed");
}
'''
functions = '\n'.join(function(sig) for sig in (
    'bool elapsed(', 'void initializeUsbSerial(', 'void initializeControlPins(', 'bool reportDue(',
    'void logCcsError(', 'void logCcsStatus(', 'void readVoc('))
with tempfile.TemporaryDirectory(prefix='aqw-application-test-') as tmp:
    cpp = Path(tmp) / 'test.cpp'
    binary = Path(tmp) / 'test'
    cpp.write_text(prefix + functions + rssi_function + tests)
    for enabled in ('true', 'false'):
        subprocess.run(['c++', '-std=c++14', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=undefined', '-DTEST_USB_WAIT_ENABLED=' + enabled,
                        str(cpp), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
