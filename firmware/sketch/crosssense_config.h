#pragma once

#include <cstddef>
#include <cstdint>

namespace crosssense {

// Bridge v1 limits. These are representation limits, not alarm thresholds.
constexpr std::size_t kMaxTracks = 8;
constexpr std::size_t kMaxEstimates = kMaxTracks;
constexpr std::size_t kMaxAlarms = 4;
constexpr std::size_t kMaxJsonBytes = 900;
constexpr std::uint32_t kObservationFrequencyHz = 5;
constexpr std::uint64_t kMaxCaptureTimeMs = 9007199254740991ULL;
constexpr std::int32_t kCoordinateLimitMm = 1000000;
constexpr std::int32_t kVelocityLimitMmS = 1000000;
constexpr std::uint32_t kMaxTtcMs = 600000;
constexpr std::uint32_t kMaxStoppingDistanceMm = 1000000;

// Zero means "not configured". No demo traffic-light timings are chosen yet.
struct SignalTimings {
  std::uint32_t vehicle_min_green_ms = 0;
  std::uint32_t pedestrian_min_green_ms = 0;
  std::uint32_t pedestrian_max_green_ms = 0;
  std::uint32_t vehicle_yellow_ms = 0;
  std::uint32_t all_red_ms = 0;
  std::uint32_t pedestrian_max_wait_ms = 0;
  std::uint32_t waiting_confirm_ms = 0;
  std::uint32_t clearance_max_ms = 0;
  std::uint32_t clear_confirm_ms = 0;
};

struct ControllerConfig {
  // Scheduling target, to be measured when the controller is implemented.
  std::uint32_t tick_ms = 10;
  std::uint32_t observation_timeout_ms = 1000;
  std::uint32_t transport_budget_ms = 250;
  SignalTimings timings{};
};

// Keep durations below half the uint32 range for later wrap-safe comparisons.
inline bool isDurationConfigured(std::uint32_t duration_ms) {
  return duration_ms > 0 && duration_ms < 0x80000000UL;
}

// Numeric completeness only; does not certify transport, hardware or safety.
inline bool isConfigurationComplete(const ControllerConfig& config) {
  const SignalTimings& t = config.timings;
  return isDurationConfigured(config.tick_ms) &&
         isDurationConfigured(config.observation_timeout_ms) &&
         config.tick_ms < config.observation_timeout_ms &&
         config.transport_budget_ms > 0 &&
         config.transport_budget_ms < config.observation_timeout_ms &&
         isDurationConfigured(t.vehicle_min_green_ms) &&
         isDurationConfigured(t.pedestrian_min_green_ms) &&
         isDurationConfigured(t.pedestrian_max_green_ms) &&
         isDurationConfigured(t.vehicle_yellow_ms) &&
         isDurationConfigured(t.all_red_ms) &&
         isDurationConfigured(t.pedestrian_max_wait_ms) &&
         isDurationConfigured(t.waiting_confirm_ms) &&
         isDurationConfigured(t.clearance_max_ms) &&
         isDurationConfigured(t.clear_confirm_ms) &&
         t.pedestrian_min_green_ms <= t.pedestrian_max_green_ms &&
         t.vehicle_min_green_ms <= t.pedestrian_max_wait_ms &&
         t.clear_confirm_ms <= t.clearance_max_ms;
}

}  // namespace crosssense
