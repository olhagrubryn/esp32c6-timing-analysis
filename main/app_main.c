#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "esp_system.h"

// ============ KONFIGURATION ============
#define MAX_TESTS 100

// ============ TIMER FUNKTIONEN ============
/**
 * @brief Gibt aktuelle Zeit in Mikrosekunden zurück
 * @return Zeit in Mikrosekunden
 */
static inline uint64_t get_time_us(void) {
    return esp_timer_get_time();
}

/**
 * @brief Schätzt Zyklen basierend auf Zeit und CPU-Frequenz
 * @return Geschätzte Zyklenanzahl
 */
static inline uint32_t estimate_cycles(uint64_t time_us) {
    // ESP32-C6 Standardfrequenz: 160 MHz
    return (uint32_t)(time_us * 160);
}

// ============ DATEN-AUSGABE FUNKTIONEN ============
/**
 * @brief Schreibt einen Header in die CSV-Ausgabe
 */
void write_csv_header(void) {
    printf("timestamp,test_name,iterations,total_time_us,time_per_op_us,ops_per_second,result_value,cpu_freq_mhz\n");
}

/**
 * @brief Schreibt Messdaten in die CSV-Ausgabe
 * @param test_name Name des Tests
 * @param total_time Gesamtzeit in Mikrosekunden
 * @param iterations Anzahl der Iterationen
 * @param time_per_op Zeit pro Operation in Mikrosekunden
 * @param ops_per_second Operationen pro Sekunde
 * @param result_value Ergebniswert der Berechnung
 */
void write_measurement_data(const char* test_name, uint64_t total_time, 
                           int iterations, double time_per_op, 
                           double ops_per_second, uint32_t result_value) {
    uint64_t timestamp = esp_timer_get_time();
    uint32_t cpu_freq = 160; // ESP32-C6 Standardfrequenz: 160 MHz
    
    printf("%" PRIu64 ",%s,%d,%" PRIu64 ",%.3f,%.0f,%" PRIu32 ",%" PRIu32 "\n", 
           timestamp, test_name, iterations, total_time, 
           time_per_op, ops_per_second, result_value, cpu_freq);
}

// ============ BENCHMARK FUNKTIONEN ============
/**
 * @brief Misst einfache ADDI-Operationen
 * Demonstriert grundlegende Integer-Arithmetik im RISC-V Befehlssatz
 */
void measure_addi_simple(void) {
    printf("=== EINFACHE ADDI ASSEMBLY MESSUNG ===\n");
    
    uint64_t start_time, end_time;
    uint32_t result = 0;
    int iterations = 10000; // Statistische Signifikanz durch viele Iterationen
    
    start_time = get_time_us();
    
    // ===== ASSEMBLY-BLOCK: Einfache ADDI-Schleife =====
    __asm__ __volatile__ (
        "mv a0, %1\n"          // Lade Iterationszähler in Register a0
        "li a1, 0\n"           // Initialisiere Ergebnisregister a1 mit 0
        "1:\n"                 // Sprunglabel für Schleifenbeginn
        "addi a1, a1, 1\n"     // ADDI: Addiere Immediate-Wert 1 zu Register a1
        "addi a0, a0, -1\n"    // Dekrementiere Iterationszähler
        "bnez a0, 1b\n"        // Branch if Not Equal Zero: Springe zu Label 1 wenn a0 != 0
        "mv %0, a1\n"          // Speichere Ergebnis zurück in C-Variable
        : "=r" (result)        // Output-Operand: Ergebnisvariable
        : "r" (iterations)     // Input-Operand: Iterationsvariable  
        : "a0", "a1"          // Clobbered Register: Welche Register verändert werden
    );
    // ===== ENDE ASSEMBLY-BLOCK =====
    
    end_time = get_time_us();
    
    // ===== BEREICHNUNG DER KENNZAHLEN =====
    uint64_t total_time = end_time - start_time;
    double time_per_op = (double)total_time / iterations;
    double ops_per_second = (double)iterations * 1000000 / total_time;
    uint32_t estimated_cycles = estimate_cycles(total_time);
    
    // ===== AUSGABE DER ERGEBNISSE =====
    printf("ADDI Operationen: %d\n", iterations);
    printf("Gesamtzeit: %" PRIu64 " us\n", total_time);
    printf("Geschätzte Zyklen: %" PRIu32 "\n", estimated_cycles);
    printf("Zeit pro ADDI: %.3f us\n", time_per_op);
    printf("Operationen pro Sekunde: %.0f\n", ops_per_second);
    printf("Ergebnis (Verifikation): %" PRIu32 "\n", result);
    
    // ===== SPEICHERUNG IN LOG-DATEI =====
    write_measurement_data("addi_simple", total_time, iterations, 
                          time_per_op, ops_per_second, result);
}

/**
 * @brief Misst mehrere ADDI-Operationen pro Iteration
 * Zeigt Pipeline-Verhalten bei aufeinanderfolgenden ADDI-Befehlen
 */
void measure_multiple_addi(void) {
    printf("=== MEHRERE ADDI OPERATIONEN PRO ITERATION ===\n");
    
    uint64_t start_time, end_time;
    uint32_t result = 0;
    int iterations = 2000; // Weniger Iterationen wegen mehr Operationen pro Durchlauf
    
    start_time = get_time_us();
    
    // ===== ASSEMBLY-BLOCK: Mehrere ADDI-Operationen =====
    __asm__ __volatile__ (
        "mv a0, %1\n"          // Iterationszähler
        "li a1, 0\n"           // Ergebnisregister
        "1:\n"
        "addi a1, a1, 1\n"     // ADDI +1
        "addi a1, a1, 2\n"     // ADDI +2 - Datenabhängigkeit von vorheriger Operation
        "addi a1, a1, 3\n"     // ADDI +3
        "addi a1, a1, 4\n"     // ADDI +4  
        "addi a1, a1, 5\n"     // ADDI +5
        "addi a0, a0, -1\n"    // Zähler dekrementieren
        "bnez a0, 1b\n"        // Schleife
        "mv %0, a1\n"          // Ergebnis zurück
        : "=r" (result)
        : "r" (iterations)
        : "a0", "a1"
    );
    // ===== ENDE ASSEMBLY-BLOCK =====
    
    end_time = get_time_us();
    
    // ===== BEREICHNUNG =====
    uint64_t total_time = end_time - start_time;
    int total_addi_ops = iterations * 5; // 5 ADDI pro Iteration
    double time_per_addi = (double)total_time / total_addi_ops;
    double ops_per_second = (double)total_addi_ops * 1000000 / total_time;
    
    printf("ADDI Operationen: %d\n", total_addi_ops);
    printf("Gesamtzeit: %" PRIu64 " us\n", total_time);
    printf("Zeit pro ADDI: %.3f us\n", time_per_addi);
    printf("Operationen pro Sekunde: %.0f\n", ops_per_second);
    printf("Ergebnis: %" PRIu32 "\n", result);
    
    write_measurement_data("multiple_addi", total_time, total_addi_ops, 
                          time_per_addi, ops_per_second, result);
}

/**
 * @brief Misst ADDI mit verschiedenen Immediate-Werten
 * Untersucht ob die Größe des Immediate-Werts die Ausführungszeit beeinflusst
 */
void measure_addi_values(void) {
    printf("=== ADDI MIT VERSCHIEDENEN IMMEDIATE-WERTEN ===\n");
    
    uint64_t start_time, end_time;
    uint32_t result = 0;
    int iterations = 3000;
    
    start_time = get_time_us();
    
    // ===== ASSEMBLY-BLOCK: Verschiedene ADDI-Werte =====
    __asm__ __volatile__ (
        "mv a0, %1\n"          // Iterationszähler
        "li a1, 0\n"           // Ergebnisregister
        "1:\n"
        "addi a1, a1, 1\n"     // Kleiner Wert (1)
        "addi a1, a1, 100\n"   // Mittlerer Wert (100)
        "addi a1, a1, 2047\n"  // Maximaler Wert für ADDI (12-bit signed)
        "addi a1, a1, -1\n"    // Negativer Wert
        "addi a0, a0, -1\n"    // Zähler dekrementieren
        "bnez a0, 1b\n"        // Schleife
        "mv %0, a1\n"          // Ergebnis zurück
        : "=r" (result)
        : "r" (iterations)
        : "a0", "a1"
    );
    // ===== ENDE ASSEMBLY-BLOCK =====
    
    end_time = get_time_us();
    
    // ===== BEREICHNUNG =====
    uint64_t total_time = end_time - start_time;
    int total_ops = iterations * 4; // 4 ADDI pro Iteration
    double time_per_op = (double)total_time / total_ops;
    double ops_per_second = (double)total_ops * 1000000 / total_time;
    
    printf("ADDI Operationen: %d\n", total_ops);
    printf("Gesamtzeit: %" PRIu64 " us\n", total_time);
    printf("Zeit pro ADDI: %.3f us\n", time_per_op);
    printf("Operationen pro Sekunde: %.0f\n", ops_per_second);
    printf("Ergebnis: %" PRIu32 "\n", result);
    
    write_measurement_data("addi_various_values", total_time, total_ops, 
                          time_per_op, ops_per_second, result);
}

/**
 * @brief Referenzmessung mit reiner C-Schleife
 * Dient als Baseline zum Vergleich mit Assembly-Implementierung
 */
void measure_c_reference(void) {
    printf("=== C-REFERENZMESSUNG (BASELINE) ===\n");
    
    uint64_t start_time, end_time;
    uint32_t result = 0;
    int iterations = 10000;
    
    start_time = get_time_us();
    
    // ===== REINE C-IMPLEMENTIERUNG =====
    for(int i = 0; i < iterations; i++) {
        result += 1; // Entspricht in etwa einer ADDI-Operation
    }
    // ===== ENDE C-IMPLEMENTIERUNG =====
    
    end_time = get_time_us();
    
    uint64_t total_time = end_time - start_time;
    double time_per_op = (double)total_time / iterations;
    double ops_per_second = (double)iterations * 1000000 / total_time;
    
    printf("C-Operationen: %d\n", iterations);
    printf("Gesamtzeit: %" PRIu64 " us\n", total_time);
    printf("Zeit pro Operation: %.3f us\n", time_per_op);
    printf("Operationen pro Sekunde: %.0f\n", ops_per_second);
    printf("Ergebnis: %" PRIu32 "\n", result);
    
    write_measurement_data("c_reference", total_time, iterations, 
                          time_per_op, ops_per_second, result);
}

// ============ HAUPTPROGRAMM ============
/**
 * @brief Hauptfunktion - Führt alle Benchmarks aus
 * Wichtige Punkte für die BA:
 * - Systeminitialisierung
 * - Warm-up Phase für stabilere Ergebnisse
 * - Wiederholte Messungen für statistische Aussagekraft
 */
void app_main(void) {
    // ===== SYSTEMINITIALISIERUNG =====
    printf("\n");
    printf("===============================================\n");
    printf("ESP32-C6 RISC-V ADDI BENCHMARK SUITE\n");
    printf("Bachelorarbeit - Mikroarchitektur-Analyse\n");
    printf("===============================================\n");
    
    // Kurze Verzögerung für stabile Serial-Ausgabe
    vTaskDelay(pdMS_TO_TICKS(2000));
    
    // ===== SYSTEMINFORMATIONEN =====
    printf("Systeminformationen:\n");
    printf("CPU: RISC-V RV32IMC\n");
    printf("Frequenz: 160 MHz\n");
    printf("Compile Time: %s %s\n", __DATE__, __TIME__);
    
    write_csv_header();
    
    // ===== WARM-UP PHASE =====
    printf("\n=== WARM-UP PHASE ===\n");
    measure_c_reference(); // Erster Durchlauf als Warm-up
    vTaskDelay(pdMS_TO_TICKS(500));
    
    int test_cycle = 0;
    
    // ===== HAUPTSCHLEIFE FÜR WIEDERHOLTE MESSUNGEN =====
    while(1) {
        test_cycle++;
        printf("\n");
        printf("=== MESSZYKLUS %d ===\n", test_cycle);
        printf("=====================\n");
        
        // ===== TESTSEQUENZ =====
        measure_c_reference();
        vTaskDelay(pdMS_TO_TICKS(100));
        
        measure_addi_simple();
        vTaskDelay(pdMS_TO_TICKS(100));
        
        measure_multiple_addi();
        vTaskDelay(pdMS_TO_TICKS(100));
        
        measure_addi_values();
        
        // ===== ZWISCHENPAUSE =====
        printf("\n--- Ende Zyklus %d - Warte 5 Sekunden ---\n", test_cycle);
        vTaskDelay(pdMS_TO_TICKS(5000));
        
        // Sicherheitsabbruch nach vielen Zyklen
        if (test_cycle >= 10) {
            printf("\n=== BENCHMARK BEENDET NACH 10 ZYKLEN ===\n");
            break;
        }
    }
    
    // ===== ABSCHLUSS =====
    printf("\n===============================================\n");
    printf("BENCHMARK ABGESCHLOSSEN\n");
    printf("Gesamte Messzyklen: %d\n", test_cycle);
    printf("Daten wurden im CSV-Format ausgegeben\n");
    printf("===============================================\n");
    
    // Endlosschleife um System am Laufen zu halten
    while(1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}