#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_cpu.h"

// Einfache Messung mit esp_cpu_get_cycle_count()
void measure_n1(void) {
    uint32_t start, end;
    
    start = esp_cpu_get_cycle_count();
    
    asm volatile (
        "li t0, 1\n"                   // n = 1
        "li t1, 0\n"                   // Zähler = 0
        "1:\n"
        "addi t1, t1, 1\n"             // Zähler erhöhen
        "bne t0, t1, 1b\n"             // Branch wenn nicht gleich
        :
        :
        : "t0", "t1"
    );
    
    end = esp_cpu_get_cycle_count();
    printf("n=1: %lu Zyklen\n", end - start);
}

void measure_n2(void) {
    uint32_t start, end;
    
    start = esp_cpu_get_cycle_count();
    
    asm volatile (
        "li t0, 2\n"                   // n = 2
        "li t1, 0\n"                   
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        :
        :
        : "t0", "t1"
    );
    
    end = esp_cpu_get_cycle_count();
    printf("n=2: %lu Zyklen\n", end - start);
}

void measure_n3(void) {
    uint32_t start, end;
    
    start = esp_cpu_get_cycle_count();
    
    asm volatile (
        "li t0, 3\n"                   // n = 3
        "li t1, 0\n"                   
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        :
        :
        : "t0", "t1"
    );
    
    end = esp_cpu_get_cycle_count();
    printf("n=3: %lu Zyklen\n", end - start);
}

void measure_n4(void) {
    uint32_t start, end;
    
    start = esp_cpu_get_cycle_count();
    
    asm volatile (
        "li t0, 4\n"                   // n = 4
        "li t1, 0\n"                   
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        :
        :
        : "t0", "t1"
    );
    
    end = esp_cpu_get_cycle_count();
    printf("n=4: %lu Zyklen\n", end - start);
}

void measure_n1000(void) {
    uint32_t start, end;
    
    start = esp_cpu_get_cycle_count();
    
    asm volatile (
        "li t0, 1000\n"                // n = 1000
        "li t1, 0\n"                   
        "1:\n"
        "addi t1, t1, 1\n"             
        "bne t0, t1, 1b\n"             
        :
        :
        : "t0", "t1"
    );
    
    end = esp_cpu_get_cycle_count();
    printf("n=1000: %lu Zyklen\n", end - start);
}

// Optimierte Version: Setup außerhalb der Messung
void measure_optimized_n1(void) {
    uint32_t start, end;
    
    // Setup außerhalb der Messung
    asm volatile (
        "li t0, 1\n"
        "li t1, 0\n"
        :
        :
        : "t0", "t1"
    );
    
    start = esp_cpu_get_cycle_count();
    
    // Nur die reine Schleife messen
    asm volatile (
        "1:\n"
        "addi t1, t1, 1\n"
        "bne t0, t1, 1b\n"
        :
        :
        : "t0", "t1"
    );
    
    end = esp_cpu_get_cycle_count();
    printf("Optimiert n=1: %lu Zyklen\n", end - start);
}

void measure_optimized_n2(void) {
    uint32_t start, end;
    
    asm volatile (
        "li t0, 2\n"
        "li t1, 0\n"
        :
        :
        : "t0", "t1"
    );
    
    start = esp_cpu_get_cycle_count();
    
    asm volatile (
        "1:\n"
        "addi t1, t1, 1\n"
        "bne t0, t1, 1b\n"
        :
        :
        : "t0", "t1"
    );
    
    end = esp_cpu_get_cycle_count();
    printf("Optimiert n=2: %lu Zyklen\n", end - start);
}

// Mehrfachmessung für bessere Genauigkeit
void measure_average_n1(void) {
    uint32_t total_cycles = 0;
    int measurements = 5;
    
    for (int i = 0; i < measurements; i++) {
        uint32_t start, end;
        
        // Setup
        asm volatile (
            "li t0, 1\n"
            "li t1, 0\n"
            :
            :
            : "t0", "t1"
        );
        
        start = esp_cpu_get_cycle_count();
        
        // Reine Schleife
        asm volatile (
            "1:\n"
            "addi t1, t1, 1\n"
            "bne t0, t1, 1b\n"
            :
            :
            : "t0", "t1"
        );
        
        end = esp_cpu_get_cycle_count();
        total_cycles += (end - start);
        
        vTaskDelay(1 / portTICK_PERIOD_MS);
    }
    
    printf("Durchschnitt n=1: %lu Zyklen\n", total_cycles / measurements);
}

// Komplette Messreihe
void run_measurements(void) {
    printf("=== Zyklus-Messung mit esp_cpu_get_cycle_count() ===\n\n");
    
    printf("Einfache Messung:\n");
    measure_n1();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_n2();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_n3();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_n4();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_n1000();
    
    printf("\nOptimierte Messung (Setup außerhalb):\n");
    measure_optimized_n1();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    measure_optimized_n2();
    vTaskDelay(10 / portTICK_PERIOD_MS);
    
    printf("\nDurchschnittsmessung:\n");
    measure_average_n1();
}

// Analyse der Ergebnisse
void analyze_results(int n1, int n2, int n3, int n4) {
    printf("\n=== Mathematische Analyse ===\n");
    
    // Gleichungssystem lösen
    int x = n1 - 1;  // n=1: 1 + x = cycles
    int y = n2 - 2 - x; // n=2: 2 + x + y = cycles
    int z = n3 - 3 - x - y; // n=3: 3 + x + y + z = cycles
    
    printf("Gemessene Werte:\n");
    printf("n=1: %d → x = %d\n", n1, x);
    printf("n=2: %d → y = %d\n", n2, y);
    printf("n=3: %d → z = %d\n", n3, z);
    
    printf("\nBerechnete Zykluszeiten:\n");
    printf("bne letzte Iteration: %d Zyklen\n", x);
    printf("bne vorletzte Iteration: %d Zyklen\n", y);
    printf("bne andere Iterationen: %d Zyklen\n", z);
    
    // Verifikation mit n=4
    int expected_n4 = 4 + x + y + 2*z;
    printf("Verifikation n=4: erwartet %d, gemessen %d → %s\n", 
           expected_n4, n4, expected_n4 == n4 ? "PASS" : "FAIL");
}

void app_main(void) {
    vTaskDelay(1000 / portTICK_PERIOD_MS);
    
    printf("=== ESP32-C6 Instruction Timing Analyse ===\n\n");
    
    run_measurements();
    
    printf("\n=== Theoretische Erwartung ===\n");
    printf("Für ESP32-C6:\n");
    printf("n=1: ~5 Zyklen (1 + x, wobei x=4)\n");
    printf("n=2: ~8 Zyklen (2 + x + y, wobei y=2)\n");
    printf("n=3: ~10 Zyklen (3 + x + y + z, wobei z=1)\n");
    printf("n=4: ~12 Zyklen (4 + x + y + 2z)\n");
    printf("n=1000: ~2004 Zyklen\n");
    
    printf("\n=== Fertig ===\n");
}