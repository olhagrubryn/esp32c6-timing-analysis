#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_cpu.h"
#include "freertos/portmacro.h"

// Kritischer Abschnitt (keine nested API mehr)
static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;

#define ENTER_CRITICAL()  portENTER_CRITICAL(&measureMux)
#define EXIT_CRITICAL()   portEXIT_CRITICAL(&measureMux)

#define MEM_BARRIER()  __asm__ __volatile__("" ::: "memory")


static inline uint32_t read_cycle_count(void)
{
    MEM_BARRIER();
    uint32_t c = esp_cpu_get_cycle_count();
    MEM_BARRIER();
    return c;
}


// -----------------------------------------------------------------------------
//  Messfunktionen
// -----------------------------------------------------------------------------

void measure_n(int n)
{
    uint32_t start, end;

    ENTER_CRITICAL();

    start = read_cycle_count();

    __asm__ __volatile__ (
        "mv t0, %0      \n"
        "li t1, 0       \n"
        "1:             \n"
        "addi t1, t1, 1 \n"
        "bne t0, t1, 1b \n"
        :
        : "r"(n)
        : "t0", "t1"
    );

    end = read_cycle_count();

    EXIT_CRITICAL();

    printf("n=%d: %lu Zyklen\n", n, (unsigned long)(end - start));
}

void measure_average_n1(void)
{
    uint32_t total = 0;

    for (int i = 0; i < 5; i++)
    {
        uint32_t start, end;

        ENTER_CRITICAL();
        start = read_cycle_count();

        __asm__ __volatile__ (
            "li t0, 1      \n"
            "li t1, 0      \n"
            "1:            \n"
            "addi t1, t1, 1\n"
            "bne t0, t1, 1b\n"
            :
            :
            : "t0", "t1"
        );

        end = read_cycle_count();
        EXIT_CRITICAL();

        total += (end - start);
        vTaskDelay(1);
    }

    printf("Durchschnitt n=1: %lu Zyklen\n", (unsigned long)(total / 5));
}


// -----------------------------------------------------------------------------
//  Aufruf
// -----------------------------------------------------------------------------

void run_measurements(void)
{
    printf("=== Zyklusmessung ===\n");
    measure_n(1);
    measure_n(2);
    measure_n(3);
    measure_n(4);
    measure_n(1000);

    printf("\nDurchschnittsmessung:\n");
    measure_average_n1();
}

void app_main(void)
{
    vTaskDelay(1000 / portTICK_PERIOD_MS);
    run_measurements();
}
