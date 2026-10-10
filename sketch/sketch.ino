#include <Arduino_RouterBridge.h>

// Diagnostica soltanto: non configura o pilota pin esterni.
String crosssenseStatus() {
  return String("scaffold_ready");
}

void setup() {
  Bridge.begin();
  Bridge.provide("crosssense_status", crosssenseStatus);
}

void loop() {
  // Il controllo delle luci e il watchdog verranno implementati dopo il cablaggio.
  delay(10);
}
