#include <cassert>
#include <cstdint>
#include <iostream>
#include <type_traits>

#include "../sketch/crosssense_types.h"

using namespace crosssense;

static_assert(std::is_trivially_copyable<ObservationFrame>::value,
              "Frames must be copyable into a bounded mailbox");
static_assert(std::is_trivially_copyable<ControllerState>::value,
              "Telemetry must be copyable into a snapshot");

void protocolExamples() {
  ObservationFrame frame;
  frame.stream = 1234;
  frame.frame = 42;
  frame.time_ms = Nullable<std::uint64_t>(58210);
  frame.age_ms = Nullable<std::uint32_t>(80);
  frame.valid = true;
  frame.crossing = CrossingState::Occupied;
  frame.approach = ApproachState::Present;
  frame.track_count = 2;
  frame.tracks[0].id = 101;
  frame.tracks[0].object_class = ObjectClass::Pedestrian;
  frame.tracks[0].zone = Zone::Crossing;
  frame.tracks[0].position = Nullable<PositionMm>(PositionMm(1200, 450));
  frame.tracks[1].id = 205;
  frame.tracks[1].object_class = ObjectClass::Vehicle;
  frame.tracks[1].zone = Zone::Approach;
  frame.tracks[1].position = Nullable<PositionMm>(PositionMm(-7500, 100));

  UpdateResponse response;
  response.frame = Nullable<std::uint32_t>(frame.frame);
  response.ok = true;
  response.error = RpcError::None;
  response.state.applied = Nullable<FrameReference>(FrameReference(1234, 41));
  response.state.uptime_ms = 2100;
  response.state.phase = Phase::PedClearance;
  response.state.observation_valid = true;
  response.state.fault = Fault::None;
  response.state.estimate_count = 1;
  VehicleEstimate& estimate = response.state.estimates[0];
  estimate.id = 205;
  estimate.vx_mm_s = Nullable<std::int32_t>(5000);
  estimate.vy_mm_s = Nullable<std::int32_t>(0);
  estimate.ttc_ms = Nullable<std::uint32_t>(1500);
  estimate.stop_mm = Nullable<std::uint32_t>(6500);

  // The receipt must not masquerade as the observation applied by the loop.
  assert(response.frame.value != response.state.applied.value.frame);
  assert(!response.state.remaining_ms.has_value);
  assert(estimate.vy_mm_s.has_value && estimate.vy_mm_s.value == 0);
  assert(frame.tracks[1].position.value.x_mm == -7500);
}

void unavailableAndZero() {
  ObservationFrame no_image;
  assert(!no_image.valid && !no_image.time_ms.has_value);
  assert(!no_image.age_ms.has_value && no_image.track_count == 0);
  assert(no_image.crossing == CrossingState::Unknown);

  ObservationFrame no_calibration;
  no_calibration.valid = true;
  no_calibration.crossing = CrossingState::Occupied;
  no_calibration.approach = ApproachState::Clear;
  no_calibration.track_count = 1;
  no_calibration.tracks[0].id = 101;
  no_calibration.tracks[0].object_class = ObjectClass::Pedestrian;
  no_calibration.tracks[0].zone = Zone::Crossing;
  assert(!no_calibration.tracks[0].position.has_value);
  assert(no_calibration.valid && no_calibration.crossing == CrossingState::Occupied);

  Nullable<PositionMm> origin(PositionMm(0, 0));
  assert(origin.has_value && origin.value.x_mm == 0 && origin.value.y_mm == 0);
  origin.clear();
  assert(!origin.has_value);
  Nullable<std::uint32_t> frame_zero(0);
  assert(frame_zero.has_value && frame_zero.value == 0);

  VehicleEstimate unavailable;
  assert(!unavailable.vx_mm_s.has_value && !unavailable.vy_mm_s.has_value);
  assert(!unavailable.ttc_ms.has_value && !unavailable.stop_mm.has_value);
}

void representationLimits() {
  ObservationFrame frame;
  frame.stream = UINT32_MAX;
  frame.frame = UINT32_MAX;
  frame.time_ms = Nullable<std::uint64_t>(kMaxCaptureTimeMs);
  frame.track_count = static_cast<std::uint8_t>(frame.tracks.size());
  for (std::size_t i = 0; i < frame.tracks.size(); ++i) {
    frame.tracks[i].id = static_cast<std::uint32_t>(i + 1);
    frame.tracks[i].position =
        Nullable<PositionMm>(PositionMm(-kCoordinateLimitMm, kCoordinateLimitMm));
  }
  const ObservationFrame copy = frame;
  assert(copy.time_ms.value > UINT32_MAX);
  assert(copy.time_ms.value == kMaxCaptureTimeMs);
  assert(copy.track_count == 8);
  assert(copy.tracks.back().position.value.x_mm == -1000000);
  assert(copy.tracks.back().position.value.y_mm == 1000000);
}

ControllerConfig configuredFixture() {
  // Test values only: these do not define the prototype's traffic-light timings.
  ControllerConfig config;
  config.timings.vehicle_min_green_ms = 5000;
  config.timings.pedestrian_min_green_ms = 3000;
  config.timings.pedestrian_max_green_ms = 7000;
  config.timings.vehicle_yellow_ms = 2000;
  config.timings.all_red_ms = 1000;
  config.timings.pedestrian_max_wait_ms = 15000;
  config.timings.waiting_confirm_ms = 500;
  config.timings.clearance_max_ms = 10000;
  config.timings.clear_confirm_ms = 500;
  return config;
}

void configurationValidation() {
  assert(!isConfigurationComplete(ControllerConfig{}));
  ControllerConfig config = configuredFixture();
  assert(isConfigurationComplete(config));
  config.timings.pedestrian_max_green_ms = 2000;
  assert(!isConfigurationComplete(config));
  config = configuredFixture();
  config.timings.pedestrian_max_wait_ms = 1000;
  assert(!isConfigurationComplete(config));
  config = configuredFixture();
  config.transport_budget_ms = config.observation_timeout_ms;
  assert(!isConfigurationComplete(config));
  config = configuredFixture();
  config.timings.clear_confirm_ms = config.timings.clearance_max_ms + 1;
  assert(!isConfigurationComplete(config));
  config = configuredFixture();
  config.timings.all_red_ms = 0x80000000UL;
  assert(!isConfigurationComplete(config));
  config = configuredFixture();
  config.tick_ms = 0;
  assert(!isConfigurationComplete(config));
}

void initialLogicalState() {
  const ControllerState state;
  assert(state.phase == Phase::Fault && state.fault == Fault::NoData);
  assert(state.vehicle_light == Light::Red && state.pedestrian_light == Light::Red);
  assert(!state.observation_valid && !state.applied.has_value);
  assert(!state.remaining_ms.has_value && !state.buzzer && !state.beacon);
  assert(state.alarm_count == 0 && state.estimate_count == 0);
}

int main() {
  protocolExamples();
  unavailableAndZero();
  representationLimits();
  configurationValidation();
  initialLogicalState();
  std::cout << "STEP1_OK: protocol examples, unavailable values, capacity, "
               "configuration and initial logical state\n"
            << "Native sizes: frame=" << sizeof(ObservationFrame)
            << " state=" << sizeof(ControllerState)
            << " response=" << sizeof(UpdateResponse) << " bytes\n";
}
