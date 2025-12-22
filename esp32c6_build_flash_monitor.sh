#!/bin/bash
#chmod +x esp32c6_build_flash_monitor.sh
#./esp32c6_build_flash_monitor.sh


# ===== Configuration =====
ESP_IDF_DIR="$HOME/esp/esp-idf"
PROJECT_DIR="$HOME/BA/esp32c6-timing-analysis-1-backup"
PORT="/dev/ttyUSB0"

# ===== Load ESP-IDF environment =====
echo "Loading ESP-IDF environment..."
cd "$ESP_IDF_DIR" || exit 1
. ./export.sh

# ===== Change to project directory =====
echo "Changing to project directory..."
cd "$PROJECT_DIR" || exit 1

# ===== Clean, build, flash, monitor =====
echo "Running fullclean..."
idf.py fullclean || exit 1

echo "Building project..."
idf.py build || exit 1

echo "Flashing firmware..."
idf.py -p "$PORT" flash || exit 1

echo "Starting monitor..."
idf.py -p "$PORT" monitor
