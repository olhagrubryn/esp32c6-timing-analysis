# test_generator.py - Angepasst für collekto.c
import subprocess
import os

# 1. Test-Verzeichnis erstellen
test_dir = "main/generated_tests"
os.makedirs(test_dir, exist_ok=True)

# 2. Test-Header-Datei generieren
header_code = """#ifndef GENERATED_TESTS_H
#define GENERATED_TESTS_H

#include <stdint.h>

uint32_t test_add(void);
uint32_t test_sub(void);
uint32_t test_and(void);
uint32_t test_or(void);
uint32_t test_xor(void);
uint32_t test_sll(void);
uint32_t test_srl(void);
uint32_t test_sra(void);
uint32_t test_slt(void);
uint32_t test_sltu(void);

#endif // GENERATED_TESTS_H
"""

# 3. Test-Implementierung generieren
test_code = """#include <stdio.h>
#include <inttypes.h>
#include "generated_tests.h"

// Performance Counter Register (adapt to your specific HW)
#define CYCLE_COUNTER_REG 0x7E2

static inline uint32_t read_cycle_counter(void) {
    uint32_t cycles;
    __asm__ __volatile__("csrr %0, %1" : "=r"(cycles) : "i"(CYCLE_COUNTER_REG));
    return cycles;
}

// Test-Makro für 1000 Wiederholungen pro Instruktion
#define RUN_TEST_BENCH(instruction, operation) \\
uint32_t instruction(void) { \\
    uint32_t start, end; \\
    uint32_t a = 0x12345678; \\
    uint32_t b = 0x87654321; \\
    uint32_t c; \\
    \\
    /* Warm-up and pipeline flush */ \\
    for (int i = 0; i < 10; i++) { \\
        __asm__ __volatile__("nop"); \\
    } \\
    \\
    start = read_cycle_counter(); \\
    \\
    /* Execute instruction 1000 times */ \\
    for (int i = 0; i < 1000; i++) { \\
        __asm__ __volatile__(#operation " %0, %1, %2" : "=r"(c) : "r"(a), "r"(b)); \\
    } \\
    \\
    end = read_cycle_counter(); \\
    \\
    /* Prevent compiler optimization */ \\
    (void)c; \\
    \\
    return end - start; \\
}

// Generiere alle Testfunktionen
RUN_TEST_BENCH(test_add, add)
RUN_TEST_BENCH(test_sub, sub)
RUN_TEST_BENCH(test_and, and)
RUN_TEST_BENCH(test_or, or)
RUN_TEST_BENCH(test_xor, xor)
RUN_TEST_BENCH(test_sll, sll)
RUN_TEST_BENCH(test_srl, srl)
RUN_TEST_BENCH(test_sra, sra)
RUN_TEST_BENCH(test_slt, slt)
RUN_TEST_BENCH(test_sltu, sltu)

// Optional: Erweiterte Tests für spezielle Fälle
uint32_t test_special_cases(void) {
    uint32_t start, end;
    uint32_t a = 0xFFFFFFFF;
    uint32_t b = 1;
    uint32_t c;
    
    start = read_cycle_counter();
    
    // Test verschiedene Operationen gemischt
    for (int i = 0; i < 250; i++) {
        __asm__ __volatile__("add %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
        __asm__ __volatile__("sub %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
        __asm__ __volatile__("and %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
        __asm__ __volatile__("or %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
    }
    
    end = read_cycle_counter();
    
    return end - start;
}
"""

# 4. Makefile für die Tests generieren
makefile_code = """# Generated Test Makefile

CC = riscv32-esp-elf-gcc
CFLAGS = -march=rv32imc -mabi=ilp32 -O2 -I$(IDF_PATH)/components/freertos/include
LDFLAGS = -nostartfiles -T$(IDF_PATH)/components/esp_rom/esp32c3/ld/esp32c3.rom.api.ld

SRCS = generated_tests.c
OBJS = $(SRCS:.c=.o)

all: libgenerated_tests.a

libgenerated_tests.a: $(OBJS)
	$(AR) rcs $@ $^

generated_tests.o: generated_tests.c generated_tests.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) libgenerated_tests.a

.PHONY: all clean
"""

# 5. Dateien schreiben
with open(f"{test_dir}/generated_tests.h", "w") as f:
    f.write(header_code)

with open(f"{test_dir}/generated_tests.c", "w") as f:
    f.write(test_code)

with open(f"{test_dir}/Makefile", "w") as f:
    f.write(makefile_code)

