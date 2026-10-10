// Arduino UNO Q: Linux chooses the LED; the MCU only applies commands.
// Built-in RGB LEDs are active LOW. No external wiring is required.
#include <Arduino_RouterBridge.h>

const int LED_PINS[] = {
  LED3_R, LED3_G, LED3_B,
  LED4_R, LED4_G, LED4_B
};

int currentLedState = 0;  // 0=off, otherwise led*10+color.
unsigned long ledChangeCount = 0;

void allLedsOff() {
  for (unsigned int i = 0; i < 6; ++i) {
    digitalWrite(LED_PINS[i], HIGH);
  }
}

// RPC: led=3 or 4; color=1 red, 2 green, 3 blue. (0, 0) turns all off.
// Returns led*10+color after applying the command, or -1 for invalid values.
int crosssense_set_led(int led, int color) {
  const bool turnOff = led == 0 && color == 0;
  if (!turnOff && ((led != 3 && led != 4) || color < 1 || color > 3)) {
    return -1;
  }

  const int nextState = led * 10 + color;
  if (nextState != currentLedState) {
    allLedsOff();
    if (!turnOff) {
      digitalWrite(LED_PINS[(led - 3) * 3 + (color - 1)], LOW);
    }
    currentLedState = nextState;
    ++ledChangeCount;
  }
  return nextState;
}

// Linux reads a counter maintained by the MCU, not a Python-side estimate.
unsigned long crosssense_get_led_change_count() {
  return ledChangeCount;
}

void setup() {
  for (unsigned int i = 0; i < 6; ++i) {
    pinMode(LED_PINS[i], OUTPUT);
    digitalWrite(LED_PINS[i], HIGH);
  }
  Bridge.begin();
  // RouterBridge dispatches this callback on the main loop thread.
  Bridge.provide_safe("crosssense_set_led", crosssense_set_led);
  Bridge.provide_safe("crosssense_get_led_change_count", crosssense_get_led_change_count);
}

void loop() {
  // No autonomous sequence. RouterBridge's loop hook services safe RPCs.
  delay(10);
}
