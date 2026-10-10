#include "../sketch/rt_protocol.h"
#include <cassert>
#include <iostream>
#include <string>
using namespace CrossSense;
std::string message(uint32_t stream,uint32_t frame,uint64_t time=100,bool request=false,uint32_t age=0) {
 JsonDocument d;
 d["stream"]=stream;d["frame"]=frame;d["time_ms"]=time;d["age_ms"]=age;d["valid"]=true;d["crossing"]="clear";d["approach"]="clear";
 d["tracks"].to<JsonArray>();auto r=d["requests"].to<JsonArray>();r.add(request);r.add(false);r.add(false);
 std::string s;serializeJson(d,s);return s;
}
void send(RTCore& rt,const std::string& raw,uint32_t now,JsonDocument& response) {rt.update(raw.c_str(),raw.size(),now,response);}
int main() {
 RTCore rt;JsonDocument response;
 auto first=message(1,1,100,true);
 send(rt,first,0,response);assert(response["ok"]==true);assert(response["applied_frame"].isNull());assert(response["phase"]=="FAULT");
 send(rt,message(1,2,101),1,response);assert(response["error"]=="BUSY");
 rt.tick(10);assert(rt.observationValid);assert(rt.requestEdges[0]==1);
 send(rt,message(1,1,100,true,600),20,response);assert(response["ok"]==true);rt.tick(21);assert(rt.requestEdges[0]==1);
 send(rt,message(1,1,100,false),22,response);assert(response["error"]=="BAD_DATA");
 send(rt,message(1,0),23,response);assert(response["error"]=="OLD_FRAME");
 send(rt,message(1,2,100),24,response);assert(response["error"]=="BAD_DATA");
 send(rt,message(1,2,101,false,750),25,response);assert(response["error"]=="STALE_FRAME");
 rt.tick(750);assert(!rt.observationValid);assert(std::string(rt.fault)=="TIMEOUT");
 send(rt,message(1,2,101),760,response);assert(response["ok"]==true);rt.tick(761);
 send(rt,message(1,3,102,true),770,response);rt.tick(771);assert(rt.requestEdges[0]==2);
 send(rt,message(2,0,1),780,response);rt.tick(781);assert(response["ok"]==true);assert(!rt.pendingRequests[0]);
 send(rt,"{}",782,response);assert(response["error"]=="BAD_DATA");assert(response["frame"].isNull());
 auto bad=message(2,1,2);JsonDocument d;deserializeJson(d,bad);auto t=d["tracks"].as<JsonArray>().add<JsonArray>();t.add(7);t.add("pedestrian");t.add("crossing");t.add(nullptr);t.add(nullptr);
 bad.clear();serializeJson(d,bad);send(rt,bad,783,response);assert(response["error"]=="BAD_DATA");
 send(rt,std::string(901,'x'),784,response);assert(response["error"]=="BAD_DATA");
 RTCore wrap;send(wrap,message(9,0xffffffff,1),0xfffffff0,response);wrap.tick(0xfffffff1);
 send(wrap,message(9,0,2),5,response);assert(response["ok"]==true);wrap.tick(6);assert(wrap.observationValid);wrap.tick(755);assert(!wrap.observationValid);
 JsonDocument absent;absent["stream"]=9;absent["frame"]=1;absent["time_ms"]=nullptr;absent["age_ms"]=nullptr;absent["valid"]=false;absent["crossing"]="unknown";absent["approach"]="unknown";absent["tracks"].to<JsonArray>();auto levels=absent["requests"].to<JsonArray>();levels.add(false);levels.add(false);levels.add(false);
 std::string missing;serializeJson(absent,missing);send(wrap,missing,756,response);assert(response["ok"]==true);wrap.tick(757);assert(std::string(wrap.fault)=="INVALID_DATA");
 assert(response["vehicle_light"]=="RED");assert(response["pedestrian_light"]=="RED");assert(response["remaining_ms"].isNull());
 std::cout<<"RT protocol checks passed: atomic buffer, duplicates, requests, watchdog, wrap, malformed frames, protected outputs.\n";
}
