#!/bin/bash
# cleanup_build.sh - Bereinigt IDF Build Probleme

echo "🧹 Bereinige Build-Verzeichnis..."
rm -rf build
rm -rf sdkconfig
rm -f sdkconfig.old

echo "📁 Überprüfe Projektstruktur..."
echo "Aktuelle Struktur:"
find . -name "*.c" -o -name "*.h" -o -name "CMakeLists.txt" | sort

echo "✅ Bereinigung abgeschlossen!"
echo ""
echo "🔄 Jetzt neu bauen:"
echo "idf.py set-target esp32c6"
echo "idf.py build"
