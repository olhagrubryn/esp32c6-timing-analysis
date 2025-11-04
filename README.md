| Supported Targets | ESP32-C6 |
| ----------------- | -------- |

# ESP32-C6 RISC-V Timing Analysis

A comprehensive benchmarking suite for analyzing RISC-V instruction timing and microarchitecture performance on ESP32-C6 processors.

## Project Overview

This project implements precise timing measurements for RISC-V assembly instructions, specifically focusing on ADDI operations, to analyze the ESP32-C6 microarchitecture. The benchmark provides:

- **Cycle-accurate timing** using ESP32-C6 hardware timers
- **Inline assembly** implementations for RISC-V instructions
- **CSV data export** for further analysis
- **Statistical measurements** with warm-up phases and repeated tests
- **Comparative analysis** between C and assembly implementations

## Research Objectives

- Measure RISC-V instruction latency on ESP32-C6
- Analyze pipeline behavior and throughput
- Characterize CPU microarchitecture performance
- Provide reproducible benchmarking methodology

## 🚀 Quick Start

### Hardware Requirements
- ESP32-C6 development board
- USB cable for programming and serial monitoring

### Software Requirements
- ESP-IDF v5.5 or later
- Python 3.x (for data analysis)

### Building and Flashing

```bash
# Clone the repository
git clone <your-repository>
cd esp32c6-timing-analysis

# Configure the project
idf.py set-target esp32c6

# Build and flash
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor

# To save results to file
idf.py -p /dev/ttyUSB0 flash monitor 2>&1 | tee benchmark_results.csv