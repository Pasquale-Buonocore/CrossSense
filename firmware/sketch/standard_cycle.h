#pragma once
#include <stdint.h>

namespace CrossSense {
// Timings for the STM32/dashboard synthetic demo, in milliseconds.
struct DemoTimings {
  uint32_t vehicleGreen = 5000;
  uint32_t vehicleYellow = 2000;
  uint32_t allRed = 1000;
  uint32_t pedestrianGreen = 5000;
  uint32_t clearanceMin = 1000;
  uint32_t clearanceMax = 10000;
  uint32_t clearConfirm = 500;
  uint32_t waitingConfirm = 800;
  uint32_t waitingRearm = 1000;
  uint32_t emptyApproachGreen = 1000;
  uint32_t accessibleGreen = 8000;
  uint32_t priorityHold = 5000;
};

enum class CyclePhase { Fault, ProtectedStop, VehicleGreen, VehicleYellow,
                        AllRedToPed, PedGreen, PedClearance, AllRedToVeh };

class StandardCycle {
 public:
  DemoTimings timings;
  CyclePhase phase = CyclePhase::Fault;
  bool consumePedestrian = false, clearanceTimeout = false, crossingConflict = false;

  void reset(uint32_t now) {
    clearanceTimeout = crossingConflict = false;
    clearTracked = false;
    accessible = priorityActive = false;
    enter(CyclePhase::Fault, now);
  }

  void tick(uint32_t now, bool valid, bool crossingClear, bool pedestrianRequest,
            bool approachPresent = true, bool accessibleRequest = false, bool priorityRequest = false) {
    consumePedestrian = false;
    if (!valid) {
      clearTracked = false;
      enter(CyclePhase::Fault, now);
      return;
    }
    if (!crossingClear) clearTracked = false;
    else if (!clearTracked) {clearTracked = true; clearSince = now;}
    const bool stableClear = clearTracked && uint32_t(now-clearSince) >= timings.clearConfirm;
    const uint32_t elapsed = now-started;
    vehicleMinimum = approachPresent?timings.vehicleGreen:timings.emptyApproachGreen;
    if (clearanceTimeout) {
      if (!stableClear) {enter(CyclePhase::ProtectedStop, now); return;}
      // Dashboard-only replay: rearm through the full clear/all-red recovery.
      clearanceTimeout = false;
      enter(CyclePhase::AllRedToVeh, now);
      return;
    }
    if (!crossingClear && (phase == CyclePhase::VehicleGreen || phase == CyclePhase::VehicleYellow)) {
      crossingConflict = true;
      enter(CyclePhase::ProtectedStop, now);
      return;
    }
    switch (phase) {
      case CyclePhase::Fault:
      case CyclePhase::ProtectedStop:
        if (stableClear) {crossingConflict = false; enter(CyclePhase::AllRedToVeh, now);}
        break;
      case CyclePhase::VehicleGreen:
        if (priorityRequest && !priorityActive) {priorityActive=true; priorityStarted=now;}
        if (priorityActive && uint32_t(now-priorityStarted)>=timings.priorityHold) priorityActive=false;
        if (pedestrianRequest && !priorityActive && elapsed >= (approachPresent?timings.vehicleGreen:timings.emptyApproachGreen)) enter(CyclePhase::VehicleYellow, now);
        break;
      case CyclePhase::VehicleYellow:
        if (elapsed >= timings.vehicleYellow) enter(CyclePhase::AllRedToPed, now);
        break;
      case CyclePhase::AllRedToPed:
        if (elapsed >= timings.allRed) {
          if (!crossingClear) enter(CyclePhase::ProtectedStop, now);
          else {consumePedestrian = true; accessible=accessibleRequest; enter(CyclePhase::PedGreen, now);}
        }
        break;
      case CyclePhase::PedGreen:
        if (elapsed >= (accessible?timings.accessibleGreen:timings.pedestrianGreen)) {
          enter(CyclePhase::PedClearance, now);
          clearTracked = false; // Require a new continuous clear window in clearance.
        }
        break;
      case CyclePhase::PedClearance:
        if (elapsed >= timings.clearanceMax) {
          clearanceTimeout = true;
          enter(CyclePhase::ProtectedStop, now);
        } else if (elapsed >= timings.clearanceMin && stableClear) enter(CyclePhase::AllRedToVeh, now);
        break;
      case CyclePhase::AllRedToVeh:
        if (!crossingClear) enter(CyclePhase::ProtectedStop, now);
        else if (elapsed >= timings.allRed && stableClear) enter(CyclePhase::VehicleGreen, now);
        break;
    }
  }

  const char* phaseName() const {
    switch (phase) {
      case CyclePhase::VehicleGreen: return "VEHICLE_GREEN";
      case CyclePhase::VehicleYellow: return "VEHICLE_YELLOW";
      case CyclePhase::AllRedToPed: return "ALL_RED_TO_PED";
      case CyclePhase::PedGreen: return "PED_GREEN";
      case CyclePhase::PedClearance: return "PED_CLEARANCE";
      case CyclePhase::AllRedToVeh: return "ALL_RED_TO_VEH";
      case CyclePhase::ProtectedStop: return "PROTECTED_STOP";
      default: return "FAULT";
    }
  }
  const char* vehicleLight() const {
    return phase == CyclePhase::VehicleGreen ? "GREEN" : phase == CyclePhase::VehicleYellow ? "YELLOW" : "RED";
  }
  const char* pedestrianLight() const {return phase == CyclePhase::PedGreen ? "GREEN" : "RED";}
  bool remaining(uint32_t now, bool pedestrianRequest, uint32_t& result) const {
    uint32_t duration;
    switch (phase) {
      case CyclePhase::VehicleGreen:
        if (!pedestrianRequest) return false;
        duration = vehicleMinimum;
        if (priorityActive) {
          const uint32_t held=now-priorityStarted;
          result=held>=timings.priorityHold?0:timings.priorityHold-held;
          const uint32_t greenElapsed=now-started;
          if (greenElapsed<duration && duration-greenElapsed>result) result=duration-greenElapsed;
          return true;
        }
        break;
      case CyclePhase::VehicleYellow: duration = timings.vehicleYellow; break;
      case CyclePhase::AllRedToPed:
      case CyclePhase::AllRedToVeh: duration = timings.allRed; break;
      case CyclePhase::PedGreen: duration = accessible?timings.accessibleGreen:timings.pedestrianGreen; break;
      default: return false; // Clearance exit depends on observations.
    }
    const uint32_t elapsed = now-started;
    result = elapsed >= duration ? 0 : duration-elapsed;
    return true;
  }

 private:
  uint32_t started = 0, clearSince = 0;
  uint32_t priorityStarted = 0;
  uint32_t vehicleMinimum = 5000;
  bool accessible = false, priorityActive = false;
  bool clearTracked = false;
  void enter(CyclePhase next, uint32_t now) {if (phase != next) {phase = next; started = now;}}
};
} // namespace CrossSense
