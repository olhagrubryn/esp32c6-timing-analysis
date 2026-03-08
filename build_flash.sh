#!/bin/bash
# build_flash.sh
#chmod +x build_flash.sh
#./build_flash.sh

# Konfiguration
PROJECT_DIR="$(pwd)"
PORT="/dev/ttyUSB0"
TARGET="esp32c6"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="benchmark_${TIMESTAMP}.txt"

# IDF-Umgebung laden
source $HOME/esp/esp-idf/export.sh

# Zum Projektverzeichnis
cd "$PROJECT_DIR"

# Target setzen
idf.py set-target $TARGET

# Bauen
echo "Building project..."
idf.py build

# Flashen
echo "Flashing to $PORT..."
idf.py -p $PORT flash

# Monitor starten und Ausgabe speichern
echo "Starting serial monitor - Ausgabe wird in ${OUTPUT_FILE} gespeichert..."
echo "Drücke Strg + ] zum Beenden"
idf.py -p $PORT monitor | tee "$OUTPUT_FILE"

echo "✅ Ausgabe gespeichert in: ${OUTPUT_FILE}"