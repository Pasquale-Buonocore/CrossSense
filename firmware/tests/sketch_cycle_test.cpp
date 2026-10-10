#include "Arduino_RouterBridge.h"
#include <cassert>
#include <iostream>
int gpioCalls=0;
unsigned long testMillis=0;
BridgeMock Bridge;
void pinMode(int,int) {++gpioCalls;}
void digitalWrite(int,int) {++gpioCalls;}
#include "../sketch/sketch.ino"

int main() {
  setup();
  assert(Bridge.handler!=nullptr);
  assert(gpioCalls==0);
  for (uint32_t now=0;now<=17000;now+=100) {
    testMillis=now;
    JsonDocument input;
    input["stream"]=1;input["frame"]=now/100+1;
    input["time_ms"]=now;input["age_ms"]=0;input["valid"]=true;
    input["crossing"]="clear";input["approach"]="clear";
    input["tracks"].to<JsonArray>();auto req=input["requests"].to<JsonArray>();
    req.add(now==1600);req.add(false);req.add(false);
    String payload;serializeJson(input,payload);
    Bridge.handler(payload);loop();
    JsonDocument response;deserializeJson(response,Bridge.handler(payload));
    if (CROSSSENSE_STANDARD_CYCLE) {
      if (now==1500 || now==16500) assert(response["vehicle_light"]=="GREEN" && response["pedestrian_light"]=="RED");
      if (now==6500) assert(response["vehicle_light"]=="YELLOW" && response["pedestrian_light"]=="RED");
      if (now==8500 || now==14500) assert(response["vehicle_light"]=="RED" && response["pedestrian_light"]=="RED");
      if (now==9500) assert(response["vehicle_light"]=="RED" && response["pedestrian_light"]=="GREEN");
    } else {
      assert(response["vehicle_light"]=="RED" && response["pedestrian_light"]=="RED");
    }
    assert(gpioCalls==0);
  }
  testMillis+=1000;loop();
  assert(std::string(rt.vehicleLight())=="RED" && std::string(rt.pedestrianLight())=="RED");
  assert(gpioCalls==0);
  std::cout << "SKETCH_OK: Bridge v1 telemetry, watchdog, zero GPIO calls, mode=" << CROSSSENSE_STANDARD_CYCLE << "\n";
}
