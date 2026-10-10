#pragma once

#include <array>
#include <cstdint>

#include "crosssense_config.h"

namespace crosssense {

// A missing value is different from a valid zero. Read value only if has_value.
template <typename T>
struct Nullable {
  bool has_value = false;
  T value{};

  Nullable() = default;
  explicit Nullable(const T& initial) : has_value(true), value(initial) {}

  void clear() {
    has_value = false;
    value = T{};
  }
};

// Wire names are specified in protocol/bridge-v1.md. JSON conversion is step 2.
enum class ObjectClass : std::uint8_t { Other, Pedestrian, Bicycle, Vehicle };
enum class Zone : std::uint8_t {
  Outside, WaitingLeft, WaitingRight, Crossing, Approach
};
enum class CrossingState : std::uint8_t { Unknown, Occupied, Clear };
enum class ApproachState : std::uint8_t { Unknown, Present, Clear };
enum class Phase : std::uint8_t {
  VehicleGreen, VehicleYellow, AllRedToPed, PedGreen, PedClearance,
  AllRedToVeh, ProtectedStop, Fault
};
enum class Light : std::uint8_t { Off, Red, Yellow, Green };
enum class Fault : std::uint8_t { None, NoData, InvalidData, Timeout };
enum class RpcError : std::uint8_t { None, BadData, OldFrame, StaleFrame, Busy };
enum class Alarm : std::uint8_t {
  CrossingConflict, CollisionRisk, PedestrianStopped, ClearanceTimeout
};

struct PositionMm {
  std::int32_t x_mm = 0;
  std::int32_t y_mm = 0;

  PositionMm() = default;
  PositionMm(std::int32_t x, std::int32_t y) : x_mm(x), y_mm(y) {}
};

struct Track {
  std::uint32_t id = 0;
  ObjectClass object_class = ObjectClass::Other;
  Zone zone = Zone::Outside;
  // One validity flag for both coordinates: partial positions cannot exist.
  Nullable<PositionMm> position{};
};

struct Requests {
  // Same order as the three booleans on the wire.
  bool pedestrian = false;
  bool accessible = false;
  bool vehicle_priority = false;
};

struct ObservationFrame {
  std::uint32_t stream = 0;
  std::uint32_t frame = 0;
  Nullable<std::uint64_t> time_ms{};
  Nullable<std::uint32_t> age_ms{};
  bool valid = false;
  CrossingState crossing = CrossingState::Unknown;
  ApproachState approach = ApproachState::Unknown;
  std::array<Track, kMaxTracks> tracks{};
  // Only [0, track_count) is populated. Step 2 must reject counts > capacity.
  std::uint8_t track_count = 0;
  Requests requests{};
};

struct FrameReference {
  std::uint32_t stream = 0;
  std::uint32_t frame = 0;

  FrameReference() = default;
  FrameReference(std::uint32_t s, std::uint32_t f) : stream(s), frame(f) {}
};

struct VehicleEstimate {
  std::uint32_t id = 0;
  Nullable<std::int32_t> vx_mm_s{};
  Nullable<std::int32_t> vy_mm_s{};
  Nullable<std::uint32_t> ttc_ms{};
  Nullable<std::uint32_t> stop_mm{};
};

struct ControllerState {
  Nullable<FrameReference> applied{};
  std::uint32_t uptime_ms = 0;
  Phase phase = Phase::Fault;
  Nullable<std::uint32_t> remaining_ms{};
  Light vehicle_light = Light::Red;
  Light pedestrian_light = Light::Red;
  bool buzzer = false;
  bool beacon = false;
  bool observation_valid = false;
  Fault fault = Fault::NoData;
  std::array<Alarm, kMaxAlarms> alarms{};
  std::uint8_t alarm_count = 0;
  std::array<VehicleEstimate, kMaxEstimates> estimates{};
  std::uint8_t estimate_count = 0;

  // Internal controller data, not extra Bridge fields.
  Requests pending_requests{};
  std::uint32_t phase_started_ms = 0;
};

struct UpdateResponse {
  // Echo of the incoming frame, independent of state.applied.
  Nullable<std::uint32_t> frame{};
  bool ok = false;
  RpcError error = RpcError::BadData;
  ControllerState state{};
};

}  // namespace crosssense
