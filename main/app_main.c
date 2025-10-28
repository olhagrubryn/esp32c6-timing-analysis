#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "esp_sleep.h"

// ============ DATEN-AUSGABE FUNKTIONEN ============
void print_csv_header(void) {
    printf("timestamp,test_name,iterations,total_time_us,time_per_op_us,ops_per_second\n");
}

void print_measurement_data(const char* test_name, uint64_t total_time, int iterations, 
                           double time_per_op, double ops_per_second) {
    uint64_t timestamp = esp_timer_get_time();
    printf("%" PRIu64 ",%s,%d,%" PRIu64 ",%.3f,%.0f\n", 
           timestamp, test_name, iterations, total_time, time_per_op, ops_per_second);
}

// ============ BENCHMARK FUNKTIONEN ============
void measure_empty_loop(int iterations) {
    printf("LEERER_SCHLEIFEN_BENCHMARK\n");
    
    uint64_t start_time = esp_timer_get_time();
    
    for (volatile int i = 0; i < iterations; i++) {
        // Leere Schleife
    }
    
    uint64_t end_time = esp_timer_get_time();
    uint64_t total_time = end_time - start_time;
    double time_per_op = (double)total_time / iterations;
    double ops_per_second = (double)iterations * 1000000 / total_time;
    
    printf("Iterationen: %d\n", iterations);
    printf("Gesamtzeit: %" PRIu64 " us\n", total_time);
    printf("Zeit pro Operation: %.3f us\n", time_per_op);
    printf("Operationen pro Sekunde: %.0f\n", ops_per_second);
    
    print_measurement_data("empty_loop", total_time, iterations, time_per_op, ops_per_second);
}

void measure_arithmetic_operations(void) {
    printf("ARITHMETISCHE_OPERATIONEN\n");
    
    int a = 123, b = 456, result = 0;
    int iterations = 100000;
    
    // Addition
    uint64_t start_time = esp_timer_get_time();
    for (int i = 0; i < iterations; i++) {
        result = a + b;
    }
    uint64_t end_time = esp_timer_get_time();
    uint64_t total_time = end_time - start_time;
    
    printf("Addition: %" PRIu64 " us\n", total_time);
    print_measurement_data("addition", total_time, iterations, 
                        (double)total_time / iterations, 
                        (double)iterations * 1000000 / total_time);
    
    // Multiplikation
    start_time = esp_timer_get_time();
    for (int i = 0; i < iterations; i++) {
        result = a * b;
    }
    end_time = esp_timer_get_time();
    total_time = end_time - start_time;
    
    printf("Multiplikation: %" PRIu64 " us\n", total_time);
    print_measurement_data("multiplication", total_time, iterations, 
                        (double)total_time / iterations, 
                        (double)iterations * 1000000 / total_time);
    
    // Division
    start_time = esp_timer_get_time();
    for (int i = 0; i < iterations; i++) {
        result = a / (b + 1);
    }
    end_time = esp_timer_get_time();
    total_time = end_time - start_time;
    
    printf("Division: %" PRIu64 " us\n", total_time);
    print_measurement_data("division", total_time, iterations, 
                        (double)total_time / iterations, 
                        (double)iterations * 1000000 / total_time);
    
    printf("Ergebnis: %d\n", result);
}

void measure_memory_access(void) {
    printf("SPEICHER_ZUGRIFFS_MUSTER\n");
    
    #define ARRAY_SIZE 100
    int array[ARRAY_SIZE];
    int iterations = 10000;
    int sum = 0;
    
    for (int i = 0; i < ARRAY_SIZE; i++) {
        array[i] = i;
    }
    
    // Sequentielle Zugriffe
    uint64_t start_time = esp_timer_get_time();
    for (int i = 0; i < iterations; i++) {
        sum += array[i % ARRAY_SIZE];
    }
    uint64_t end_time = esp_timer_get_time();
    uint64_t total_time = end_time - start_time;
    
    printf("Sequentielle Zugriffe: %" PRIu64 " us\n", total_time);
    print_measurement_data("sequential_access", total_time, iterations, 
                        (double)total_time / iterations, 
                        (double)iterations * 1000000 / total_time);
    
    printf("Summe: %d\n", sum);
}

void measure_floating_point(void) {
    printf("GLEITKOMMA_OPERATIONEN\n");
    
    float a = 123.456f, b = 789.012f, result = 0.0f;
    int iterations = 50000;
    
    // Float Addition
    uint64_t start_time = esp_timer_get_time();
    for (int i = 0; i < iterations; i++) {
        result = a + b;
    }
    uint64_t end_time = esp_timer_get_time();
    uint64_t total_time = end_time - start_time;
    
    printf("Float Addition: %" PRIu64 " us\n", total_time);
    print_measurement_data("float_addition", total_time, iterations, 
                        (double)total_time / iterations, 
                        (double)iterations * 1000000 / total_time);
    
    // Float Multiplikation
    start_time = esp_timer_get_time();
    for (int i = 0; i < iterations; i++) {
        result = a * b;
    }
    end_time = esp_timer_get_time();
    total_time = end_time - start_time;
    
    printf("Float Multiplikation: %" PRIu64 " us\n", total_time);
    print_measurement_data("float_multiplication", total_time, iterations, 
                        (double)total_time / iterations, 
                        (double)iterations * 1000000 / total_time);
    
    printf("Ergebnis: %.3f\n", result);
}

// ============ TIMER MESSUNGEN ============
static volatile uint32_t timer_callback_count = 0;

void IRAM_ATTR timer_callback(void* arg) {
    timer_callback_count++;
}

void measure_timer_performance(void) {
    printf("TIMER_LEISTUNGSMESSUNG\n");
    
    esp_timer_handle_t periodic_timer;
    const esp_timer_create_args_t timer_args = {
        .callback = &timer_callback,
        .name = "performance_timer"
    };
    
    esp_err_t ret = esp_timer_create(&timer_args, &periodic_timer);
    if (ret != ESP_OK) {
        printf("Timer Erstellung fehlgeschlagen\n");
        return;
    }
    
    timer_callback_count = 0;
    uint64_t start_time = esp_timer_get_time();
    
    ret = esp_timer_start_periodic(periodic_timer, 100000);
    if (ret != ESP_OK) {
        printf("Timer Start fehlgeschlagen\n");
        esp_timer_delete(periodic_timer);
        return;
    }
    
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    uint64_t end_time = esp_timer_get_time();
    esp_timer_stop(periodic_timer);
    esp_timer_delete(periodic_timer);
    
    uint64_t total_time = end_time - start_time;
    
    printf("Timer-Callbacks: %" PRIu32 "\n", timer_callback_count);
    printf("Tatsaechliche Zeit: %" PRIu64 " us\n", total_time);
    
    print_measurement_data("timer_performance", total_time, timer_callback_count, 
                         (double)total_time / timer_callback_count, 
                         (double)timer_callback_count * 1000000 / total_time);
}

void measure_function_call_overhead(void) {
    printf("FUNKTIONS_AUFRUF_OVERHEAD\n");
    
    int iterations = 100000;
    
    uint64_t start_time = esp_timer_get_time();
    
    for (int i = 0; i < iterations; i++) {
        esp_timer_get_time();
    }
    
    uint64_t end_time = esp_timer_get_time();
    uint64_t total_time = end_time - start_time;
    double time_per_call = (double)total_time / iterations;
    
    printf("Funktionsaufrufe: %d\n", iterations);
    printf("Gesamtzeit: %" PRIu64 " us\n", total_time);
    printf("Zeit pro Funktionsaufruf: %.3f us\n", time_per_call);
    
    print_measurement_data("function_call", total_time, iterations, time_per_call, 
                        (double)iterations * 1000000 / total_time);
}

// ============ SCHLAFMODUS TEST ============
void measure_sleep_modes(void) {
    printf("SCHLAFMODUS_TEST\n");
    
    printf("Aktiver Modus - 1 Sekunde\n");
    uint64_t active_start = esp_timer_get_time();
    vTaskDelay(pdMS_TO_TICKS(1000));
    uint64_t active_end = esp_timer_get_time();
    
    printf("Aktiver Modus Zeit: %" PRIu64 " us\n", active_end - active_start);
    
    printf("Light Sleep - 500ms\n");
    esp_sleep_enable_timer_wakeup(500000);
    uint64_t sleep_start = esp_timer_get_time();
    esp_light_sleep_start();
    uint64_t sleep_end = esp_timer_get_time();
    
    printf("Light Sleep Zeit: %" PRIu64 " us\n", sleep_end - sleep_start);
    
    print_measurement_data("light_sleep", sleep_end - sleep_start, 1, 
                         (double)(sleep_end - sleep_start), 0);
}

// ============ KOMPLETTER BENCHMARK ============
void run_complete_benchmark(void) {
    printf("BEGIN_BENCHMARK_SUITE\n");
    printf("ESP32_C6_BENCHMARK_DATA\n");
    printf("Compile_Time: %s %s\n", __DATE__, __TIME__);
    
    print_csv_header();
    
    measure_empty_loop(1000000);
    measure_arithmetic_operations();
    measure_memory_access();
    measure_floating_point();
    measure_function_call_overhead();
    measure_timer_performance();
    measure_sleep_modes();
    
    printf("END_BENCHMARK_SUITE\n");
    printf("BENCHMARK_ABGESCHLOSSEN\n");
}

// ============ HAUPTPROGRAMM ============
void app_main(void) {
    vTaskDelay(pdMS_TO_TICKS(4000));
    
    printf("ESP32_C6_BENCHMARK_START\n");
    printf("Chip_Revision: v0.1\n");
    printf("CPU_Frequency: 160 MHz\n");
    printf("ESP_IDF_Version: v5.5\n");
    
    run_complete_benchmark();
    
    int cycle_count = 0;
    while (1) {
        cycle_count++;
        printf("CYCLE_RESTART_%d\n", cycle_count);
        vTaskDelay(pdMS_TO_TICKS(30000));
        run_complete_benchmark();
    }
}