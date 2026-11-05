// UNO Q bench receiver. No CAN transmit entry point. See docs/RUNBOOK.md.
#include <Arduino.h>
#include <Arduino_RouterBridge.h>
#include <zephyr/drivers/can.h>
#include <zephyr/kernel.h>
#include <zephyr/random/random.h>
#include <zephyr/sys/atomic.h>
#include <zephyrPinctrl.h>
#include <stdio.h>
#include <string.h>

#ifndef CAPTURE_FD
#define CAPTURE_FD 0
#endif
static constexpr uint32_t NOMINAL_BITRATE = 500000;
static constexpr uint32_t DATA_BITRATE = 2000000;
static const struct device *const canDev = DEVICE_DT_GET(DT_NODELABEL(fdcan1));
struct Record { struct can_frame frame; uint64_t us; uint32_t seq; };
K_MSGQ_DEFINE(rxQueue, sizeof(Record), 64, 8);
static atomic_t receivedCount, droppedCount;
static int initError = -EAGAIN;
static bool running = false, everStarted = false, held = false;
static can_mode_t capabilities = 0;
static uint32_t batch = 0;
static char bootId[17];
static Record pending;

static void receiveFrame(const struct device *, struct can_frame *frame, void *) {
  Record r{};
  r.seq = static_cast<uint32_t>(atomic_inc(&receivedCount)) + 1U;
  r.us = k_ticks_to_us_floor64(k_uptime_ticks());
  r.frame = *frame;
  if (k_msgq_put(&rxQueue, &r, K_NO_WAIT) != 0) atomic_inc(&droppedCount);
}

static int prepareCan() {
  int rc = zephyr::arduino::init_dev_apply_pinctrl(canDev);
  if (rc < 0) return rc;
  if (!device_is_ready(canDev)) return -ENODEV;
  rc = can_stop(canDev);
  if (rc < 0 && rc != -EALREADY) return rc;
  rc = can_get_capabilities(canDev, &capabilities);
  if (rc < 0) return rc;
  const can_mode_t mode = CAN_MODE_LISTENONLY | (CAPTURE_FD ? CAN_MODE_FD : 0);
  if ((capabilities & mode) != mode) return -ENOTSUP;
  rc = can_set_mode(canDev, mode);
  if (rc < 0) return rc;
  rc = can_set_bitrate(canDev, NOMINAL_BITRATE);
  if (rc < 0) return rc;
#if CAPTURE_FD
#if defined(CONFIG_CAN_FD_MODE)
  rc = can_set_bitrate_data(canDev, DATA_BITRATE);
  if (rc < 0) return rc;
#else
  return -ENOTSUP;
#endif
#endif
  struct can_filter standard{};
  struct can_filter extended{};
  extended.flags = CAN_FILTER_IDE;
  int sf = can_add_rx_filter(canDev, receiveFrame, nullptr, &standard);
  if (sf < 0) return sf;
  int ef = can_add_rx_filter(canDev, receiveFrame, nullptr, &extended);
  if (ef < 0) { can_remove_rx_filter(canDev, sf); return ef; }
  // Remains stopped until Linux has opened its durable capture files.
  return 0;
}

static int startCapture() {
  if (initError != 0) return initError;
  if (everStarted) return -EALREADY; // New capture requires an intentional MCU reset.
  int rc = can_start(canDev);
  if (rc == 0) { running = true; everStarted = true; }
  return rc;
}

static int stopCapture() {
  if (!running) return 0;
  int rc = can_stop(canDev);
  if (rc == 0) running = false;
  return rc;
}

static String captureStatus() {
  enum can_state state = CAN_STATE_STOPPED;
  struct can_bus_err_cnt errors{};
  int rc = initError == 0 ? can_get_state(canDev, &state, &errors) : initError;
  char out[240];
  int written = snprintf(out, sizeof(out),
    "{\"v\":1,\"boot\":\"%s\",\"init\":%d,\"running\":%d,\"started\":%d,\"fd\":%d,\"rx\":%lu,\"drop\":%lu,\"q\":%u,\"held\":%d,\"state\":%d,\"rec\":%u,\"tec\":%u,\"rc\":%d,\"tick_hz\":%u}",
    bootId, initError, running, everStarted, CAPTURE_FD,
    (unsigned long)(uint32_t)atomic_get(&receivedCount),
    (unsigned long)(uint32_t)atomic_get(&droppedCount),
    k_msgq_num_used_get(&rxQueue), held, (int)state, errors.rx_err_cnt,
    errors.tx_err_cnt, rc, (unsigned)CONFIG_SYS_CLOCK_TICKS_PER_SEC);
  if (written < 0 || written >= (int)sizeof(out)) return String("ERROR: status size");
  return String(out);
}

static String readCapture(uint32_t ack) {
  // Keep the last record until Linux acknowledges it AFTER fsync.
  // A repeated request with the preceding ack returns the same record.
  if (held && ack == batch) held = false;
  if (!held && k_msgq_get(&rxQueue, &pending, K_NO_WAIT) == 0) {
    ++batch;
    held = true;
  }
  char out[240];
  if (!held) {
    snprintf(out, sizeof(out), "[\"%s\",0,null]", bootId);
    return String(out);
  }
  const uint8_t n = (pending.frame.flags & CAN_FRAME_RTR) ? 0 : can_dlc_to_bytes(pending.frame.dlc);
  char hex[129];
  const char *digits = "0123456789abcdef";
  for (uint8_t i = 0; i < n; ++i) {
    hex[2*i] = digits[pending.frame.data[i] >> 4];
    hex[2*i+1] = digits[pending.frame.data[i] & 15];
  }
  hex[2*n] = 0;
  int written = snprintf(out, sizeof(out), "[\"%s\",%lu,[%lu,%llu,%lu,%u,%u,\"%s\"]]",
    bootId, (unsigned long)batch, (unsigned long)pending.seq,
    (unsigned long long)pending.us, (unsigned long)pending.frame.id,
    pending.frame.flags, pending.frame.dlc, hex);
  if (written < 0 || written >= (int)sizeof(out)) return String("ERROR: record size");
  return String(out);
}

void setup() {
  snprintf(bootId, sizeof(bootId), "%08lx%08lx", (unsigned long)sys_rand32_get(), (unsigned long)sys_rand32_get());
  initError = prepareCan();
  if (!Bridge.begin()) { (void)stopCapture(); return; }
  // Register start last. Any registration failure leaves CAN stopped.
  if (!Bridge.provide("capture.status", captureStatus)) return;
  if (!Bridge.provide("capture.read", readCapture)) return;
  if (!Bridge.provide("capture.stop", stopCapture)) return;
  (void)Bridge.provide("capture.start", startCapture);
}
void loop() { delay(10); }
