#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import re
import serial
import time
from datetime import datetime

def parse_serial_data(port='/dev/ttyUSB0', baudrate=115200, timeout=10):
    """Liest Daten vom ESP32 und extrahiert Benchmark-Ergebnisse"""
    print("📡 Verbinde mit ESP32...")
    
    results = {
        'test_names': [],
        'times_us': [],
        'iterations': [],
        'ops_per_second': []
    }
    
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"✅ Verbunden mit {port}")
        
        # Warte auf Start
        start_time = time.time()
        while time.time() - start_time < timeout:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            if "RUNNING COMPLETE BENCHMARK SUITE" in line:
                print("🚀 Benchmark gestartet - sammle Daten...")
                break
                
            if line:
                print(f"ESP32: {line}")
        
        # Sammle Benchmark-Daten
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            if not line:
                continue
                
            print(f"ESP32: {line}")
            
            # Extrahiere Benchmark-Ergebnisse
            if ":" in line and "µs" in line and "Iterations" not in line:
                # Beispiel: "Empty Loop: 1000000 iterations, 12345 µs"
                if "Iterations" in line:
                    try:
                        # Testname extrahieren
                        test_name = line.split(':')[0].strip()
                        
                        # Iterations extrahieren
                        iter_match = re.search(r'Iterations:\s*(\d+)', line)
                        iterations = int(iter_match.group(1)) if iter_match else 0
                        
                        # Zeit extrahieren
                        time_match = re.search(r'Total Time:\s*(\d+)\s*µs', line)
                        time_us = int(time_match.group(1)) if time_match else 0
                        
                        if test_name and time_us > 0:
                            results['test_names'].append(test_name)
                            results['times_us'].append(time_us)
                            results['iterations'].append(iterations)
                            results['ops_per_second'].append(iterations * 1000000 / time_us)
                            
                            print(f"📊 Gesammelt: {test_name} - {time_us} µs")
                    except Exception as e:
                        print(f"❌ Fehler beim Parsen: {e}")
            
            # Stoppe wenn Benchmarks fertig
            if "ALL BENCHMARKS COMPLETED" in line:
                print("✅ Alle Benchmarks abgeschlossen")
                break
                
            # Timeout
            if time.time() - start_time > 60:  # 60 Sekunden Timeout
                print("⏰ Timeout - beende Datensammlung")
                break
                
        ser.close()
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
    
    return results

def create_plots(results):
    """Erstellt Diagramme aus den gesammelten Daten"""
    if not results['test_names']:
        print("❌ Keine Daten zum Plotten gefunden")
        return
    
    print(f"📈 Erstelle Diagramme für {len(results['test_names'])} Tests...")
    
    # Daten vorbereiten
    test_names = results['test_names']
    times_ms = [t / 1000 for t in results['times_us']]  # µs zu ms
    ops_per_second = results['ops_per_second']
    
    # 1. Balkendiagramm - Ausführungszeiten
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    bars = plt.bar(test_names, times_ms, color='skyblue', edgecolor='black')
    plt.title('Ausführungszeit pro Benchmark', fontsize=14, fontweight='bold')
    plt.ylabel('Zeit (ms)')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3)
    
    # Werte auf Balken anzeigen
    for bar, time_ms in zip(bars, times_ms):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(times_ms)*0.01, 
                f'{time_ms:.1f}ms', ha='center', va='bottom', fontsize=8)
    
    # 2. Balkendiagramm - Operationen pro Sekunde
    plt.subplot(2, 2, 2)
    bars = plt.bar(test_names, ops_per_second, color='lightgreen', edgecolor='black')
    plt.title('Operationen pro Sekunde', fontsize=14, fontweight='bold')
    plt.ylabel('Ops/Sekunde')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3)
    
    # 3. Laufzeit-Verteilung (Pie Chart)
    plt.subplot(2, 2, 3)
    colors = plt.cm.Set3(np.linspace(0, 1, len(test_names)))
    plt.pie(times_ms, labels=test_names, autopct='%1.1f%%', colors=colors)
    plt.title('Laufzeit-Verteilung', fontsize=14, fontweight='bold')
    
    # 4. Performance-Vergleich (normalisiert)
    plt.subplot(2, 2, 4)
    normalized_perf = [max(ops_per_second) / ops if ops > 0 else 0 for ops in ops_per_second]
    bars = plt.bar(test_names, normalized_perf, color='lightcoral', edgecolor='black')
    plt.title('Performance-Vergleich (normalisiert)', fontsize=14, fontweight='bold')
    plt.ylabel('Relative Performance')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    # Diagramm speichern
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_{timestamp}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"💾 Diagramm gespeichert als: {filename}")
    
    plt.show()

def create_simple_plot():
    """Erstellt ein einfaches Beispiel-Diagramm falls keine Live-Daten"""
    print("📊 Erstelle Beispiel-Diagramm...")
    
    # Beispiel-Daten (falls Serial nicht funktioniert)
    example_data = {
        'test_names': ['Empty Loop', 'Function Call', 'Arithmetic', 'Memory Access', 'Floating Point'],
        'times_us': [15234, 8921, 15678, 23456, 34567],
        'iterations': [1000000, 100000, 100000, 100000, 100000],
        'ops_per_second': [65623412, 11209595, 6378976, 4262341, 2892345]
    }
    
    create_plots(example_data)

if __name__ == "__main__":
    print("🎯 ESP32-C6 Benchmark Data Plotter")
    print("=" * 50)
    
    # Versuche Live-Daten zu sammeln
    results = parse_serial_data()
    
    if results['test_names']:
        create_plots(results)
    else:
        print("⚠️  Keine Live-Daten gefunden, erstelle Beispiel-Diagramm...")
        create_simple_plot()