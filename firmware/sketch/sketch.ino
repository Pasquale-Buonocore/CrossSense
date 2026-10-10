// Bridge v1 receiver. Controller commissioning mode: both built-in RGB LEDs red.
#include <Arduino_RouterBridge.h>
#include "rt_protocol.h"

CrossSense::RTCore rt;
const int LED_PINS[] = {LED3_R,LED3_G,LED3_B,LED4_R,LED4_G,LED4_B};

String crosssense_update(String frameJson) {
  JsonDocument response;
  rt.update(frameJson.c_str(),frameJson.length(),uint32_t(millis()),response);
  char buffer[CrossSense::PayloadLimit+1];
  serializeJson(response,buffer,sizeof(buffer));
  return String(buffer);
}

void setup() {
  for (int pin:LED_PINS) {pinMode(pin,OUTPUT);digitalWrite(pin,HIGH);}
  digitalWrite(LED3_R,LOW);digitalWrite(LED4_R,LOW);
  Bridge.begin();
  Bridge.provide_safe("crosssense_update",crosssense_update);
}

void loop() {
  rt.tick(uint32_t(millis()));
  delay(10);
}
