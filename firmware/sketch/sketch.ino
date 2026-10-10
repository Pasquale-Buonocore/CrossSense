// Bridge v1 receiver. Signal outputs are telemetry for the Linux dashboard.
#include <Arduino_RouterBridge.h>
#include "rt_protocol.h"

#ifndef CROSSSENSE_STANDARD_CYCLE
#define CROSSSENSE_STANDARD_CYCLE 0
#endif
CrossSense::RTCore rt(CROSSSENSE_STANDARD_CYCLE != 0);

String crosssense_update(String frameJson) {
  JsonDocument response;
  rt.update(frameJson.c_str(),frameJson.length(),uint32_t(millis()),response);
  char buffer[CrossSense::PayloadLimit+1];
  serializeJson(response,buffer,sizeof(buffer));
  return String(buffer);
}

void setup() {
  Bridge.begin();
  Bridge.provide_safe("crosssense_update",crosssense_update);
}

void loop() {
  rt.tick(uint32_t(millis()));
  delay(10);
}
