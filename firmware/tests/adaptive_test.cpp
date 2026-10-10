#include "../sketch/rt_protocol.h"
#include <cassert>
#include <iostream>
#include <string>
using namespace CrossSense;

void sample(RTCore& rt,uint32_t now,bool waiting,bool approach=true,bool accessible=false,bool priority=false) {
  JsonDocument input,response;
  input["stream"]=1;input["frame"]=now+1;input["time_ms"]=now;
  input["age_ms"]=0;input["valid"]=true;input["crossing"]="clear";
  input["approach"]=approach?"present":"clear";
  auto tracks=input["tracks"].to<JsonArray>();
  if(waiting){auto t=tracks.add<JsonArray>();t.add(1);t.add("pedestrian");t.add("waiting_left");t.add(nullptr);t.add(nullptr);}
  auto requests=input["requests"].to<JsonArray>();requests.add(false);requests.add(accessible);requests.add(priority);
  std::string raw;serializeJson(input,raw);
  rt.update(raw.c_str(),raw.size(),now,response);assert(response["ok"]==true);rt.tick(now);
  assert(!(std::string(rt.vehicleLight())=="GREEN"&&std::string(rt.pedestrianLight())=="GREEN"));
}
int main(){
  RTCore busy(true),empty(true);
  for(uint32_t t=0;t<=2500;t+=100){sample(busy,t,true);sample(empty,t,true,false);}
  assert(busy.cycle.phase==CyclePhase::VehicleGreen);
  assert(empty.cycle.phase==CyclePhase::VehicleYellow);
  for(uint32_t t=2600;t<=9500;t+=100)sample(busy,t,true);
  assert(busy.cycle.phase==CyclePhase::PedGreen);
  assert(!busy.pendingRequests[0]);
  // A continuously waiting group creates only one request until absent/rearmed.
  for(uint32_t t=9600;t<=20000;t+=100)sample(busy,t,true);
  assert(busy.cycle.phase==CyclePhase::VehicleGreen);
  for(uint32_t t=20100;t<=21200;t+=100)sample(busy,t,false);
  for(uint32_t t=21300;t<=22200;t+=100)sample(busy,t,true);
  assert(busy.cycle.phase==CyclePhase::VehicleYellow);
  RTCore accessible(true);
  for(uint32_t t=0;t<=17000;t+=100)sample(accessible,t,false,true,t==1600);
  assert(accessible.cycle.phase==CyclePhase::PedGreen); // 8s instead of 5s.
  RTCore priority(true);
  for(uint32_t t=0;t<=6500;t+=100)sample(priority,t,true,true,false,t==1600);
  assert(priority.cycle.phase==CyclePhase::VehicleGreen);
  sample(priority,6600,true);assert(priority.cycle.phase==CyclePhase::VehicleYellow);
  assert(!priority.pendingRequests[2]);
  std::cout<<"ADAPTIVE_OK: automatic dwell, one-shot/rearm, approach, accessible time, bounded priority\n";
}
