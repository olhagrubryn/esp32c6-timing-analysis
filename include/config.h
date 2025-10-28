#ifndef CONFIG_H
#define CONFIG_H

// Firmware Version
#define FIRMWARE_VERSION "1.0.0"

// Pin Definitions
#define BENCHMARK_GPIO_OUT      2
#define BENCHMARK_GPIO_IN       4
#define INTERRUPT_TEST_PIN      5

// Benchmark Settings
#define DEFAULT_ITERATIONS      100000
#define WARMUP_ITERATIONS       1000

// Timing Constants
#define CPU_FREQUENCY_MHZ       160
#define NS_PER_CYCLE            (1000 / CPU_FREQUENCY_MHZ)

#endif