#include "../sketch/rt_protocol.h"
#include <cassert>
#include <iostream>
#include <string>
using namespace CrossSense;

struct Harness {
  RTCore rt{true};
  JsonDocument response;
  uint32_t stream=1, sequence=0, now=0;
  bool hasSample=false, lastClear=true, lastRequest=false, lastValid=true;
  std::string last;

  void sample(uint32_t at, bool clear=true, bool request=false, bool valid=true) {
    // Keep real fresh observations flowing while advancing virtual time.
    while (hasSample && uint32_t(at-now)>200) sample(now+200,lastClear,lastRequest,lastValid);
    now=at;
    hasSample=true;lastClear=clear;lastRequest=request;lastValid=valid;
    JsonDocument input;
    input["stream"]=stream; input["frame"]=++sequence;
    input["time_ms"]=sequence; input["age_ms"]=0; input["valid"]=valid;
    input["crossing"]=valid?(clear?"clear":"occupied"):"unknown";
    input["approach"]=valid?"clear":"unknown";
    input["tracks"].to<JsonArray>();
    auto requests=input["requests"].to<JsonArray>();
    requests.add(request);requests.add(false);requests.add(false);
    last.clear();serializeJson(input,last);
    rt.update(last.c_str(),last.size(),now,response);
    assert(response["ok"]==true);
    rt.tick(now);
    read();
  }
  void read() {rt.update(last.c_str(),last.size(),now,response);}
  void expect(const char* phase,const char* vehicle="RED",const char* pedestrian="RED") {
    if (response["phase"]!=phase) std::cerr << "at=" << now << " expected=" << phase << " actual=" << response["phase"].as<const char*>() << "\n";
    assert(response["phase"]==phase);
    assert(response["vehicle_light"]==vehicle);
    assert(response["pedestrian_light"]==pedestrian);
    assert(!(response["vehicle_light"]=="GREEN" && response["pedestrian_light"]=="GREEN"));
  }
  void start(uint32_t base=0) {
    sample(base);expect("FAULT");
    sample(base+499);expect("FAULT");
    sample(base+500);expect("ALL_RED_TO_VEH");
    sample(base+1499);expect("ALL_RED_TO_VEH");
    sample(base+1500);expect("VEHICLE_GREEN","GREEN");
  }
  void pedestrian() {
    start();
    sample(1600,true,true);expect("VEHICLE_GREEN","GREEN");
    assert(response["remaining_ms"]==4900);
    sample(6499);expect("VEHICLE_GREEN","GREEN");
    sample(6500);expect("VEHICLE_YELLOW","YELLOW");
    sample(8499);expect("VEHICLE_YELLOW","YELLOW");
    sample(8500);expect("ALL_RED_TO_PED");
    sample(9499);expect("ALL_RED_TO_PED");
    sample(9500);expect("PED_GREEN","RED","GREEN");
    assert(!rt.pendingRequests[0]);
    sample(14499,false);expect("PED_GREEN","RED","GREEN");
    sample(14500,false);expect("PED_CLEARANCE");
    assert(response["remaining_ms"].isNull());
  }
};

int main() {
  Harness standard;standard.pedestrian();
  standard.sample(14510);standard.sample(15499);standard.expect("PED_CLEARANCE");
  standard.sample(15500);standard.expect("ALL_RED_TO_VEH");
  standard.sample(16499);standard.expect("ALL_RED_TO_VEH");
  standard.sample(16500);standard.expect("VEHICLE_GREEN","GREEN");
  standard.sample(26500);standard.expect("VEHICLE_GREEN","GREEN");
  assert(standard.response["remaining_ms"].isNull()); // No request, no fixed deadline.
  standard.sample(26600,true,true);standard.expect("VEHICLE_YELLOW","YELLOW");

  Harness occupied;occupied.pedestrian();
  occupied.sample(15500,false);occupied.expect("PED_CLEARANCE");
  occupied.sample(20000,false);occupied.expect("PED_CLEARANCE");
  occupied.sample(20010);occupied.sample(20509);occupied.expect("PED_CLEARANCE");
  occupied.sample(20510);occupied.expect("ALL_RED_TO_VEH");
  occupied.sample(20520,false);occupied.expect("PROTECTED_STOP"); // Reoccupation vetoes release.

  Harness timeout;timeout.pedestrian();
  timeout.sample(24500,false);timeout.expect("PROTECTED_STOP");
  assert(timeout.response["alarms"][0]=="CLEARANCE_TIMEOUT");
  timeout.sample(25000);timeout.sample(26000);timeout.expect("PROTECTED_STOP");
  ++timeout.stream;timeout.sample(26010);timeout.expect("FAULT"); // New session rearms through clear recovery.
  timeout.sample(26510);timeout.expect("ALL_RED_TO_VEH");

  Harness fault;fault.start();
  fault.now=2250;fault.read();fault.expect("FAULT"); // RPC itself detects stale data.
  assert(fault.response["fault"]=="TIMEOUT");
  fault.sample(2300);fault.expect("FAULT");
  fault.sample(2800);fault.expect("ALL_RED_TO_VEH");
  fault.sample(3800);fault.expect("VEHICLE_GREEN","GREEN");
  fault.sample(3810,true,false,false);fault.expect("FAULT");
  assert(fault.response["fault"]=="INVALID_DATA");

  // Loss of data closes every normal phase, without skipping protected recovery.
  const CyclePhase normal[] = {CyclePhase::VehicleGreen,CyclePhase::VehicleYellow,
    CyclePhase::AllRedToPed,CyclePhase::PedGreen,CyclePhase::PedClearance,CyclePhase::AllRedToVeh};
  for (auto phase:normal) {
    StandardCycle cycle;cycle.phase=phase;cycle.tick(10,false,false,true);
    assert(cycle.phase==CyclePhase::Fault);
    assert(std::string(cycle.vehicleLight())=="RED");
    assert(std::string(cycle.pedestrianLight())=="RED");
  }

  Harness conflict;conflict.start();
  conflict.sample(1600,false);conflict.expect("PROTECTED_STOP");
  assert(conflict.response["alarms"][0]=="CROSSING_CONFLICT");
  conflict.sample(1700);conflict.sample(2199);conflict.expect("PROTECTED_STOP");
  conflict.sample(2200);conflict.expect("ALL_RED_TO_VEH");
  assert(conflict.response["alarms"].size()==0);

  Harness restart;restart.start();++restart.stream;
  restart.sample(1700);restart.expect("FAULT");
  restart.sample(2200);restart.expect("ALL_RED_TO_VEH");

  Harness wrap;wrap.start(0xfffffa00U);
  wrap.sample(uint32_t(0xfffffa00U+1600U),true,true);
  wrap.sample(uint32_t(0xfffffa00U+6500U));wrap.expect("VEHICLE_YELLOW","YELLOW");
  std::cout << "STANDARD_CYCLE_OK: sequence, minimum times, requests, occupancy, clearance timeout, fault recovery, stream reset, clock wrap\n";
}
