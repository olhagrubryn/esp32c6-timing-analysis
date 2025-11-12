#!/bin/bash

echo "Starte ESP32 Build-Prozess in $(pwd)"

# Prüfe ob IDF_PATH gesetzt ist
if [ -z "$IDF_PATH" ]; then
    echo "IDF_PATH nicht gesetzt!"
    echo "Bitte zuerst: source ~/esp/esp-idf/export.sh"
    exit 1
fi

echo "Bitte manuell: STRG-T + STRG-X drücken falls nötig"
echo " Drücke ENTER um fortzufahren..."
read

echo "Clean..."
idf.py fullclean || exit 1

echo "Build..."
idf.py build || exit 1

echo "Flash..."
idf.py flash || exit 1

echo "Monitor..."
idf.py -p /dev/ttyUSB0 monitor