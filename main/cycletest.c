#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_attr.h"
#include <inttypes.h>

// Hardware-Zykluszähler
static inline void init_performance_counters(void) {
    __asm__ __volatile__ (
        "li t0, 0x01 \n"
        "csrw 0x7E0, t0 \n"   // Aktiviert Zykluszählung
        "csrw 0x7E1, t0 \n"   // Aktiviert Zähler
        "csrw 0x7E2, x0 \n"   // Setzt Zähler auf 0
        ::: "t0"
    );
}

static inline uint32_t get_hardware_cycle_count(void) {
    uint32_t val;
    __asm__ __volatile__ ("csrr %0, 0x7E2" : "=r"(val));
    return val;
}

// Kritischer Abschnitt (verhindert Unterbrechungen)
static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;
#define ENTER_CRITICAL()  portENTER_CRITICAL(&measureMux)
#define EXIT_CRITICAL()   portEXIT_CRITICAL(&measureMux)

FORCE_INLINE_ATTR IRAM_ATTR uint32_t measure_isolated_add(void)
{
    uint32_t start, end;
    uint32_t a = 1, b = 2, r;

    ENTER_CRITICAL();

    start = get_hardware_cycle_count();

    __asm__ __volatile__ (
        "add %0, %1, %2\n"
        : "=r"(r)
        : "r"(a), "r"(b)
    );

    end = get_hardware_cycle_count();

    EXIT_CRITICAL();

    return end - start;
}

// Hauptfunktion
void app_main(void)
{
    init_performance_counters();

    for (int i = 0; i < 10; i++) {
        uint32_t c = measure_isolated_add();
        printf("isolierte ADD: %" PRIu32 " Zyklen\n", c);
    }
}
