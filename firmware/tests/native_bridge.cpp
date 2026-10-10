// Line-based host runner for the actual sketch. Not firmware for the board.
#include "Arduino_RouterBridge.h"
#include <cassert>
#include <cstdlib>
#include <iostream>
unsigned long testMillis=0;
BridgeMock Bridge;
void pinMode(int,int) {assert(false && "The sketch must not configure GPIO");}
void digitalWrite(int,int) {assert(false && "The sketch must not write GPIO");}
#include "../sketch/sketch.ino"
int main() {
  setup();
  std::string line;
  while (std::getline(std::cin,line)) {
    const auto split=line.find(' ');
    if (split==std::string::npos) return 2;
    testMillis=std::strtoul(line.substr(0,split).c_str(),nullptr,10);
    loop();
    const String response=Bridge.handler(line.substr(split+1));
    loop();
    std::cout << response << std::endl;
  }
}
