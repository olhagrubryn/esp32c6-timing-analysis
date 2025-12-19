#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_cpu.h"
#include "freertos/portmacro.h"

// -----------------------------------------------------------------------------
//  Kritischer Abschnitt
// -----------------------------------------------------------------------------

static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;

#define ENTER_CRITICAL()  portENTER_CRITICAL(&measureMux)
#define EXIT_CRITICAL()   portEXIT_CRITICAL(&measureMux)

#define MEM_BARRIER() __asm__ __volatile__("" ::: "memory")

static inline uint32_t read_cycle_count(void)
{
    MEM_BARRIER();
    uint32_t c = esp_cpu_get_cycle_count();
    MEM_BARRIER();
    return c;
}

// -----------------------------------------------------------------------------
//  Cache Warmup
// -----------------------------------------------------------------------------

__attribute__((noinline))
void cache_warmup(void)
{
    volatile int x = 0;
    for (int i = 0; i < 1000; i++)
    {
        x += i;
    }
}

// -----------------------------------------------------------------------------
//  Messung: Overhead
// -----------------------------------------------------------------------------

uint32_t measure_overhead(void)
{
    uint32_t start, end;

    ENTER_CRITICAL();
    start = read_cycle_count();

    __asm__ __volatile__ ("" ::: "memory");

    end = read_cycle_count();
    EXIT_CRITICAL();

    return end - start;
}

// -----------------------------------------------------------------------------
//  Messung: ALU ADD Latenz (abhängige Kette)
// -----------------------------------------------------------------------------

uint32_t measure_add_latency(void)
{
    uint32_t start, end;

    ENTER_CRITICAL();
    start = read_cycle_count();

    __asm__ __volatile__ (
        "li t0, 1 \n"
        "li t1, 2 \n"
        // 32 abhängige ADDs (reicht völlig)
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        "add t0, t0, t1 \n"
        :
        :
        : "t0", "t1"
    );

    end = read_cycle_count();
    EXIT_CRITICAL();

    return end - start;
}

// -----------------------------------------------------------------------------
//  Messung: Vergleich + abhängige Nutzung (SLT)
// -----------------------------------------------------------------------------

uint32_t measure_slt_latency(void)
{
    uint32_t start, end;

    ENTER_CRITICAL();
    start = read_cycle_count();

    __asm__ __volatile__ (
        "li t1, 5 \n"
        "li t2, 10 \n"
        "li t3, 0 \n"

        "slt t0, t1, t2 \n"
        "add t3, t3, t0 \n"
        "slt t0, t1, t2 \n"
        "add t3, t3, t0 \n"
        "slt t0, t1, t2 \n"
        "add t3, t3, t0 \n"
        "slt t0, t1, t2 \n"
        "add t3, t3, t0 \n"
        :
        :
        : "t0", "t1", "t2", "t3"
    );

    end = read_cycle_count();
    EXIT_CRITICAL();

    return end - start;
}

// -----------------------------------------------------------------------------
//  Messung: Branch Prediction
// -----------------------------------------------------------------------------

uint32_t measure_branch_good(void)
{
    uint32_t start, end;

    ENTER_CRITICAL();
    start = read_cycle_count();

    __asm__ __volatile__ (
        "li t0, 0 \n"
        "li t1, 50 \n"
        "1: \n"
        "addi t0, t0, 1 \n"
        "blt t0, t1, 1b \n"
        :
        :
        : "t0", "t1"
    );

    end = read_cycle_count();
    EXIT_CRITICAL();

    return end - start;
}

uint32_t measure_branch_bad(void)
{
    uint32_t start, end;

    ENTER_CRITICAL();
    start = read_cycle_count();

    __asm__ __volatile__ (
        "li t0, 0 \n"
        "li t1, 50 \n"
        "li t2, 0 \n"
        "1: \n"
        "xori t2, t2, 1 \n"
        "beq t2, zero, 2f \n"
        "addi t0, t0, 1 \n"
        "2: \n"
        "blt t0, t1, 1b \n"
        :
        :
        : "t0", "t1", "t2"
    );

    end = read_cycle_count();
    EXIT_CRITICAL();

    return end - start;
}

// -----------------------------------------------------------------------------
//  Messung: Write-Back Pressure
// -----------------------------------------------------------------------------

uint32_t measure_writeback_pressure(void)
{
    uint32_t start, end;

    ENTER_CRITICAL();
    start = read_cycle_count();

    __asm__ __volatile__ (
        "add t0, t1, t2 \n"
        "add t3, t4, t5 \n"
        "add t6, s0, s1 \n"
        "add s2, s3, s4 \n"
        "add s5, s6, s7 \n"
        :
        :
        : "t0","t1","t2","t3","t4","t5",
          "t6","s0","s1","s2","s3","s4","s5","s6","s7"
    );

    end = read_cycle_count();
    EXIT_CRITICAL();

    return end - start;
}

// -----------------------------------------------------------------------------
//  Hauptmessung
// -----------------------------------------------------------------------------

void run_measurements(void)
{
    cache_warmup(); 
    vTaskDelay(10);

    uint32_t overhead = measure_overhead();
    printf("Overhead: %lu Zyklen\n\n", overhead);

    uint32_t add = measure_add_latency() - overhead;
    printf("ADD-Kette: %lu Zyklen (16 ADDs)\n", add);

    uint32_t slt = measure_slt_latency() - overhead;
    printf("SLT+ADD: %lu Zyklen\n", slt);

    uint32_t bg = measure_branch_good() - overhead;
    uint32_t bb = measure_branch_bad() - overhead;
    printf("Branch gut: %lu | schlecht: %lu | Penalty: %lu\n",
           bg, bb, bb - bg);

    uint32_t wb = measure_writeback_pressure() - overhead;
    printf("Writeback Pressure: %lu Zyklen\n", wb);
}

void app_main(void)
{
    vTaskDelay(1000 / portTICK_PERIOD_MS);
    run_measurements();
}
