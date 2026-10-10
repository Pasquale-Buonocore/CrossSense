#pragma once
#include <ArduinoJson.h>
#include <stdint.h>
#include <string.h>
#include "standard_cycle.h"

namespace CrossSense {
constexpr uint32_t Deadline = 1000, TransportBudget = 250;
constexpr size_t PayloadLimit = 900;
struct Track {
  uint32_t id = 0;
  uint8_t kind = 0, zone = 0;
  bool metric = false;
  int32_t x = 0, y = 0;
};
struct Frame {
  uint32_t stream = 0, frame = 0, age = 0;
  uint64_t time = 0;
  bool image = false, valid = false, requests[3] = {};
  uint8_t crossing = 0, approach = 0, count = 0;
  Track tracks[8];
};
inline uint8_t choice(JsonVariantConst v, const char* const* choices, uint8_t n) {
  if (!v.is<const char*>()) return 255;
  for (uint8_t i=0;i<n;++i) if (strcmp(v.as<const char*>(),choices[i])==0) return i;
  return 255;
}
inline bool parse(JsonDocument& doc, Frame& f) {
  const char* const crossings[] = {"unknown","occupied","clear"};
  const char* const approaches[] = {"unknown","present","clear"};
  const char* const kinds[] = {"pedestrian","bicycle","vehicle","other"};
  const char* const zones[] = {"waiting_left","waiting_right","crossing","approach","outside"};
  const char* const keys[] = {"stream","frame","time_ms","age_ms","valid","crossing","approach","tracks","requests"};
  if (!doc.is<JsonObject>() || doc.size()!=9) return false;
  for (auto key: keys) if (!doc[key].is<JsonVariant>()) return false;
  if (!doc["stream"].is<uint32_t>() || !doc["frame"].is<uint32_t>() || !doc["valid"].is<bool>()) return false;
  f.stream=doc["stream"];f.frame=doc["frame"];f.valid=doc["valid"];
  f.crossing=choice(doc["crossing"],crossings,3);f.approach=choice(doc["approach"],approaches,3);
  if (f.crossing==255 || f.approach==255) return false;
  if (!doc["tracks"].is<JsonArray>() || doc["tracks"].size()>8 || !doc["requests"].is<JsonArray>() || doc["requests"].size()!=3) return false;
  for (uint8_t i=0;i<3;++i) {
    if (!doc["requests"][i].is<bool>()) return false;
    f.requests[i]=doc["requests"][i];
  }
  f.image=!doc["time_ms"].isNull();
  if (f.image) {
    if (!doc["time_ms"].is<uint64_t>() || doc["time_ms"].as<uint64_t>()>9007199254740991ULL || !doc["age_ms"].is<uint32_t>()) return false;
    f.time=doc["time_ms"];f.age=doc["age_ms"];
  } else if (!doc["age_ms"].isNull() || f.valid || doc["tracks"].size()!=0 || f.crossing!=0 || f.approach!=0) return false;
  if ((!f.valid && (f.crossing==2 || f.approach==2)) || (f.valid && (f.crossing==0 || f.approach==0))) return false;
  for (JsonVariantConst value:doc["tracks"].as<JsonArrayConst>()) {
    if (!value.is<JsonArrayConst>() || value.size()!=5) return false;
    auto a=value.as<JsonArrayConst>();Track& t=f.tracks[f.count];
    if (!a[0].is<uint32_t>() || a[0].as<uint32_t>()==0) return false;
    t.id=a[0];t.kind=choice(a[1],kinds,4);t.zone=choice(a[2],zones,5);
    if (t.kind==255 || t.zone==255) return false;
    for (uint8_t j=0;j<f.count;++j) if (f.tracks[j].id==t.id) return false;
    t.metric=!(a[3].isNull() && a[4].isNull());
    if (t.metric) {
      if (!a[3].is<int32_t>() || !a[4].is<int32_t>()) return false;
      t.x=a[3];t.y=a[4];
      if (t.x < -1000000 || t.x > 1000000 || t.y < -1000000 || t.y > 1000000) return false;
    }
    if ((t.kind!=2 && t.zone==2 && f.crossing==2) || (t.kind==2 && t.zone==3 && f.approach==2)) return false;
    ++f.count;
  }
  return true;
}
inline bool same(const Frame& a,const Frame& b) {
  if (a.stream!=b.stream || a.frame!=b.frame || a.image!=b.image || a.time!=b.time || a.valid!=b.valid || a.crossing!=b.crossing || a.approach!=b.approach || a.count!=b.count) return false;
  for (uint8_t i=0;i<3;++i) if (a.requests[i]!=b.requests[i]) return false;
  for (uint8_t i=0;i<a.count;++i) {
    auto x=a.tracks[i],y=b.tracks[i];
    if (x.id!=y.id || x.kind!=y.kind || x.zone!=y.zone || x.metric!=y.metric || x.x!=y.x || x.y!=y.y) return false;
  }
  return true; // Retry may update age_ms only.
}

class RTCore {
 public:
  explicit RTCore(bool standardCycle = false) : cycleEnabled(standardCycle) {}
  StandardCycle cycle;
  Frame accepted, applied;
  bool hasAccepted=false, hasApplied=false, pending=false, observationValid=false;
  bool requestLevels[3]={}, pendingRequests[3]={};
  uint32_t requestEdges[3]={};
  const char* fault="NO_DATA";

  void tick(uint32_t now) {
    if (pending) {
      const bool reset=!hasApplied || applied.stream!=accepted.stream;
      if (reset) {
        for (uint8_t i=0;i<3;++i) {requestLevels[i]=false;pendingRequests[i]=false;}
        cycle.reset(now);
        waitingTracked=false; waitingArmed=true; absenceTracked=false;
      }
      applied=accepted;hasApplied=true;pending=false;appliedAt=acceptedAt;
      for (uint8_t i=0;i<3;++i) {
        if (applied.requests[i] && !requestLevels[i]) {pendingRequests[i]=true;++requestEdges[i];}
        requestLevels[i]=applied.requests[i];
      }
      if (pendingRequests[1]) pendingRequests[0]=true;
    }
    tickWatchdog(now);
    if (cycleEnabled) {
      bool waiting=false;
      for (uint8_t i=0;i<applied.count;++i) {
        const Track& t=applied.tracks[i];
        if ((t.kind==0 || t.kind==1) && (t.zone==0 || t.zone==1)) waiting=true;
      }
      if (!observationValid) {waitingTracked=false; absenceTracked=false;}
      else if (waiting) {
        absenceTracked=false;
        if (!waitingTracked) {waitingTracked=true; waitingSince=now;}
        if (waitingArmed && uint32_t(now-waitingSince)>=cycle.timings.waitingConfirm) {
          pendingRequests[0]=true; waitingArmed=false;
        }
      } else {
        waitingTracked=false;
        if (!absenceTracked) {absenceTracked=true; absentSince=now;}
        if (uint32_t(now-absentSince)>=cycle.timings.waitingRearm) waitingArmed=true;
      }
      const bool priority=pendingRequests[2] && cycle.phase==CyclePhase::VehicleGreen && observationValid;
      cycle.tick(now,observationValid,applied.crossing==2,pendingRequests[0],applied.approach==1,pendingRequests[1],priority);
      if (priority) pendingRequests[2]=false;
      if (cycle.consumePedestrian) {pendingRequests[0]=false;pendingRequests[1]=false;}
    }
  }

  const char* vehicleLight() const {return cycleEnabled?cycle.vehicleLight():"RED";}
  const char* pedestrianLight() const {return cycleEnabled?cycle.pedestrianLight():"RED";}

  void update(const char* raw,size_t length,uint32_t now,JsonDocument& response) {
    JsonDocument input;
    Frame f;
    const char* error="BAD_DATA";
    bool ok=false;
    bool readable=false;uint32_t receivedFrame=0;
    if (length<=PayloadLimit && !deserializeJson(input,raw,length,DeserializationOption::NestingLimit(4))) {
      readable=input["frame"].is<uint32_t>();
      if (readable) receivedFrame=input["frame"];
      if (parse(input,f)) {
        if (hasAccepted && f.stream==accepted.stream && f.frame==accepted.frame) {
          ok=same(f,accepted);error=ok?nullptr:"BAD_DATA";
        } else if (hasAccepted && f.stream==accepted.stream && !newer(f.frame,accepted.frame)) {
          error="OLD_FRAME";
        } else if (hasAccepted && f.stream==accepted.stream && f.image && hasCapture && f.time<=captureTime) {
          error="BAD_DATA";
        } else if (f.valid && uint64_t(f.age)+TransportBudget>=Deadline) {
          error="STALE_FRAME";
        } else if (pending) {
          error="BUSY";
        } else {
          if (!hasAccepted || accepted.stream!=f.stream) hasCapture=false;
          accepted=f;acceptedAt=now;hasAccepted=true;pending=true;
          if (f.image) {captureTime=f.time;hasCapture=true;}
          ok=true;error=nullptr;
        }
      }
    }
    // State describes the frame already consumed by loop(), never the pending frame.
    tickWatchdog(now);
    // A callback can detect a timeout before the next loop tick. Close greens;
    // only loop() may consume data, serve requests or advance normal phases.
    if (cycleEnabled && !observationValid) cycle.tick(now,false,false,false);
    response.clear();
    if (readable) response["frame"]=receivedFrame;else response["frame"]=nullptr;
    response["ok"]=ok;response["error"]=error;
    if (hasApplied) {response["applied_stream"]=applied.stream;response["applied_frame"]=applied.frame;}
    else {response["applied_stream"]=nullptr;response["applied_frame"]=nullptr;}
    response["uptime_ms"]=now;
    response["phase"]=cycleEnabled?cycle.phaseName():(observationValid?"PROTECTED_STOP":"FAULT");
    uint32_t remaining=0;
    if (cycleEnabled && cycle.remaining(now,pendingRequests[0],remaining)) response["remaining_ms"]=remaining;
    else response["remaining_ms"]=nullptr;
    response["vehicle_light"]=vehicleLight();response["pedestrian_light"]=pedestrianLight();
    response["buzzer"]=false;response["beacon"]=false;
    response["observation_valid"]=observationValid;response["fault"]=fault;
    auto alarms=response["alarms"].to<JsonArray>();
    if (cycleEnabled && cycle.crossingConflict) alarms.add("CROSSING_CONFLICT");
    if (cycleEnabled && cycle.clearanceTimeout) alarms.add("CLEARANCE_TIMEOUT");
    response["estimates"].to<JsonArray>();
  }
 private:
  bool cycleEnabled;
  uint32_t acceptedAt=0,appliedAt=0;
  uint64_t captureTime=0;
  bool hasCapture=false;
  bool waitingTracked=false, waitingArmed=true, absenceTracked=false;
  uint32_t waitingSince=0, absentSince=0;
  static bool newer(uint32_t n,uint32_t old) {uint32_t d=n-old;return d!=0 && d<0x80000000UL;}
  void tickWatchdog(uint32_t now) {
    // Do not consume pending data inside the RPC callback.
    if (!hasApplied) {observationValid=false;fault="NO_DATA";}
    else if (!applied.valid) {observationValid=false;fault="INVALID_DATA";}
    else {observationValid=uint64_t(applied.age)+TransportBudget+uint32_t(now-appliedAt)<Deadline;fault=observationValid?nullptr:"TIMEOUT";}
  }
};
} // namespace CrossSense
