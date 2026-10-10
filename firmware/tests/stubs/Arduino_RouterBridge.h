#pragma once
#include <string>
using String = std::string;
enum {HIGH=1,LOW=0,OUTPUT=1};
enum {LED3_R,LED3_G,LED3_B,LED4_R,LED4_G,LED4_B};
extern int pins[6];
extern unsigned long testMillis;
inline unsigned long millis() {return testMillis;}
void pinMode(int,int);
void digitalWrite(int,int);
inline void delay(int duration) {testMillis+=duration;}
struct BridgeMock {
  String (*handler)(String) = nullptr;
  void begin() {}
  void provide_safe(const char*,String (*callback)(String)) {handler=callback;}
};
extern BridgeMock Bridge;
