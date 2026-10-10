#include <Arduino_RouterBridge.h>

// Transport smoke test only. No traffic light outputs are configured.
unsigned long crosssense_ping() {
  return millis();
}

void setup() {
  Bridge.begin();
  Bridge.provide("crosssense_ping", crosssense_ping);
}

void loop() {
  delay(10);
}
