#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// Messung mit korrekt konfigurierten Performance Countern
void measure_n1(void) {
    uint32_t start_cycles, end_cycles;
    
    asm volatile (
        "li t0, 1\n"                   // n = 1
        "li t1, 0\n"                   // Zähler = 0
        
        // Performance Counter korrekt konfigurieren
        "csrw 0x7E0, 1\n"              // Count CPU cycles (nicht zero!)
        "csrw 0x7E1, 1\n"              // Enable counter (nicht zero!)
        "csrr %0, 0x7E2\n"             // Startwert lesen -> t0
        
        // Zu messender Code
        "1:\n"
        "addi t1, t1, 1\n"             // Zähler erhöhen
        "bne t0, t1, 1b\n"             // Branch wenn nicht gleich
        
        // Performance Counter Endwert lesen
        "csrr %1, 0x7E2\n"             // Endwert lesen -> t1
        : "=r" (start_cycles), "=r" (end_cycles)
        :
        : "t0", "t1"
    );
    
    printf("n=1: %lu Zyklen\n", end_cycles - start_cycles);
}

void measure_n2(void) {
    uint32_t start_cycles, end_cycles;
    
    asm volatile (
        "li t0, 2\n"                   // n = 2
        "li t1, 0\n"                   
        
        "csrw 0x7E0, 1\n"              // Count CPU cycles
        "csrw 0x7E1, 1\n"              // Enable counter
        "csrr %0, 0x7E2\n"             // Startwert lesen
        
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        
        "csrr %1, 0x7E2\n"             // Endwert lesen
        : "=r" (start_cycles), "=r" (end_cycles)
        :
        : "t0", "t1"
    );
    
    printf("n=2: %lu Zyklen\n", end_cycles - start_cycles);
}

void measure_n3(void) {
    uint32_t start_cycles, end_cycles;
    
    asm volatile (
        "li t0, 3\n"                   // n = 3
        "li t1, 0\n"                   
        
        "csrw 0x7E0, 1\n"              // Count CPU cycles
        "csrw 0x7E1, 1\n"              // Enable counter
        "csrr %0, 0x7E2\n"             // Startwert lesen
        
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        
        "csrr %1, 0x7E2\n"             // Endwert lesen
        : "=r" (start_cycles), "=r" (end_cycles)
        :
        : "t0", "t1"
    );
    
    printf("n=3: %lu Zyklen\n", end_cycles - start_cycles);
}

void measure_n4(void) {
    uint32_t start_cycles, end_cycles;
    
    asm volatile (
        "li t0, 4\n"                   // n = 4
        "li t1, 0\n"                   
        
        "csrw 0x7E0, 1\n"              // Count CPU cycles
        "csrw 0x7E1, 1\n"              // Enable counter
        "csrr %0, 0x7E2\n"             // Startwert lesen
        
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        
        "csrr %1, 0x7E2\n"             // Endwert lesen
        : "=r" (start_cycles), "=r" (end_cycles)
        :
        : "t0", "t1"
    );
    
    printf("n=4: %lu Zyklen\n", end_cycles - start_cycles);
}

void measure_n1000(void) {
    uint32_t start_cycles, end_cycles;
    
    asm volatile (
        "li t0, 1000\n"                // n = 1000
        "li t1, 0\n"                   
        
        "csrw 0x7E0, 1\n"              // Count CPU cycles
        "csrw 0x7E1, 1\n"              // Enable counter
        "csrr %0, 0x7E2\n"             // Startwert lesen
        
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        
        "csrr %1, 0x7E2\n"             // Endwert lesen
        : "=r" (start_cycles), "=r" (end_cycles)
        :
        : "t0", "t1"
    );
    
    printf("n=1000: %lu Zyklen\n", end_cycles - start_cycles);
}

// Präzise Version mit exakt den Registern aus der Dokumentation
void measure_precise_n1(void) {
    uint32_t cycles;
    
    asm volatile (
        "li t0, 1\n"                   // n = 1
        "li t1, 0\n"                   // Zähler = 0
        
        // Performance Counter konfigurieren
        "csrw 0x7E0, 1\n"              // Count CPU cycles
        "csrw 0x7E1, 1\n"              // Enable counter
        
        // Startwert lesen (t2 wie in Dokumentation)
        "csrr t2, 0x7E2\n"             
        
        // Zu messender Code
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        
        // Endwert lesen (t3 wie in Dokumentation) und Subtraktion
        "csrr t3, 0x7E2\n"             
        "sub %0, t3, t2\n"             // Zyklen = t3 - t2
        : "=r" (cycles)
        :
        : "t0", "t1", "t2", "t3"
    );
    
    printf("Präzise n=1: %lu Zyklen\n", cycles);
}

void measure_precise_n2(void) {
    uint32_t cycles;
    
    asm volatile (
        "li t0, 2\n"                   
        "li t1, 0\n"                   
        
        "csrw 0x7E0, 1\n"              
        "csrw 0x7E1, 1\n"              
        "csrr t2, 0x7E2\n"             
        
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        
        "csrr t3, 0x7E2\n"             
        "sub %0, t3, t2\n"             
        : "=r" (cycles)
        :
        : "t0", "t1", "t2", "t3"
    );
    
    printf("Präzise n=2: %lu Zyklen\n", cycles);
}

// Noch präzisere Version - exakt wie in der Dokumentation
void measure_exact_n1(void) {
    uint32_t cycles;
    
    asm volatile (
        // Setup wie in Dokumentation
        "li t0, 1\n"                   // {n} iterations
        "li t1, 0\n"                   // counter = 0
        
        // Configure and read performance counter (EXAKT wie im Text)
        "csrw 0x7E0, 1\n"              // Count CPU cycles
        "csrw 0x7E1, 1\n"              // Enable counter
        "csrr t2, 0x7E2\n"             // Read start -> t2
        
        // Run the code we want to measure (EXAKT wie im Text)
        "1:\n"
        "addi t1, t1, 1\n"             // Increment counter
        "bne t0, t1, 1b\n"             // Loop if t1 != t0
        
        // Read the performance counter again (EXAKT wie im Text)
        "csrr t3, 0x7E2\n"             // Read end -> t3
        
        // Calculate cycles
        "sub %0, t3, t2\n"             // cycles = end - start
        : "=r" (cycles)
        :
        : "t0", "t1", "t2", "t3"
    );
    
    printf("Exakt n=1: %lu Zyklen\n", cycles);
}

// Komplette Messreihe
void run_measurements(void) {
    printf("=== Zyklus-Messung mit Performance Countern ===\n\n");
    
    printf("Standard Messung:\n");
    measure_n1();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_n2();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_n3();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_n4();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_n1000();
    
    printf("\nPräzise Messung:\n");
    measure_precise_n1();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_precise_n2();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    printf("\nExakte Messung (wie Dokumentation):\n");
    measure_exact_n1();
}

// Analyse der Ergebnisse
void show_expected_analysis(void) {
    printf("\n=== Theoretische Analyse ===\n");
    printf("Erwartete Werte für ESP32-C6:\n");
    printf("n=1: 5 Zyklen  → 1 + x = 5 → x = 4\n");
    printf("n=2: 8 Zyklen  → 2 + x + y = 8 → y = 2\n");
    printf("n=3: 10 Zyklen → 3 + x + y + z = 10 → z = 1\n");
    printf("n=4: 12 Zyklen → 4 + x + y + 2z = 12 → Bestätigung\n");
    printf("n=1000: 2004 Zyklen → 1000 + x + y + 998z = 2004 → Bestätigung\n");
    
    printf("\nZusammenfassung:\n");
    printf("bne benötigt:\n");
    printf("- 4 Zyklen in letzter Iteration (Branch nicht genommen)\n");
    printf("- 2 Zyklen in vorletzter Iteration\n");
    printf("- 1 Zyklus in anderen Iterationen (Branch genommen)\n");
}

void app_main(void) {
    vTaskDelay(1000 / portTICK_PERIOD_MS);
    
    printf("=== ESP32-C6 Instruction Timing Analyse ===\n");
    printf("Using Hardware Performance Counters (csrw 0x7E0,1 / csrw 0x7E1,1)\n\n");
    
    run_measurements();
    show_expected_analysis();
    
    printf("\n=== Fertig ===\n");
}

// ACHTUNG: Der C-Code muss die Performance-Counter vor dem Aufruf dieser Funktion
// einmalig initialisieren (csrw 0x7E0, 1; csrw 0x7E1, 1).
// Das verbleibende Ergebnis wird NICHT 5 Zyklen betragen, da der Branch-Penalty
// (ca. 30-50 Zyklen) NICHT VERMEIDBAR ist.

void measure_n1_optimized(void) {
    uint32_t start_cycles, end_cycles;
    
    asm volatile (
        // 1. Setup-Instruktionen aus dem Messbereich entfernen, falls möglich,
        // oder direkt am Anfang setzen, falls der Zustand nicht persistent ist.
        // Hier lassen wir sie für die Vollständigkeit.
        "csrw 0x7E0, 1\n"              // Count CPU cycles
        "csrw 0x7E1, 1\n"              // Enable counter
        
        // C-Compiler sollte diese beiden Variablen in t0 und t1 laden.
        // Das Laden wird nicht gemessen.
        "li t0, 1\n"                   // n = 1
        "li t1, 0\n"                   // Zähler = 0
        
        // Zähler START SOFORT VOR dem zu messenden Code lesen
        "csrr %0, 0x7E2\n"             // Startwert lesen -> %0 (start_cycles)
        
        // Zu messender Code (reine Schleife)
        "1:\n"
        "addi t1, t1, 1\n"             // Zähler erhöhen (1 Zyklus)
        "bne t0, t1, 1b\n"             // Branch wenn nicht gleich (1 Zyklus + Penalty)
        
        // Zähler ENDE SOFORT NACH dem zu messenden Code lesen
        "csrr %1, 0x7E2\n"             // Endwert lesen -> %1 (end_cycles)
        
        // KEINE Instruktionen hier, da sie gemessen werden!
        
        : "=r" (start_cycles), "=r" (end_cycles) // Output-Register für %0 und %1
        :
        : "t0", "t1" // Clobber (t0 und t1 werden geändert)
    );
    
    printf("n=1 (Optimized): %lu Zyklen\n", end_cycles - start_cycles);
}