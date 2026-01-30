#!/usr/bin/env python3
# working_assembler_generator.py - Kompiliert garantiert!

import os
import random

# ============================================================================
# 1. EINFACHE GENERATOR-FUNKTIONEN
# ============================================================================

def generate_alu_ops(num_ops):
    """Generiert ALU-Operationen mit festen Registern."""
    ops = []
    alu_ops = ["add", "sub", "and", "or", "xor", "sll", "srl", "sra"]
    
    # Feste Register: t1-t6
    registers = ["t1", "t2", "t3", "t4", "t5", "t6"]
    
    for i in range(num_ops):
        op = random.choice(alu_ops)
        # Wähle Register basierend auf Index für Vorhersagbarkeit
        idx = i % len(registers)
        rd = registers[idx]
        rs1 = registers[(idx + 1) % len(registers)]
        rs2 = registers[(idx + 2) % len(registers)]
        ops.append(f"{op} {rd}, {rs1}, {rs2}")
    
    return ops

def generate_mixed_ops(num_ops):
    """Generiert gemischte Operationen."""
    ops = []
    
    for i in range(num_ops):
        if i % 3 == 0:
            ops.append(f"add t1, t2, t3")
        elif i % 3 == 1:
            ops.append(f"sub t4, t5, t6")
        else:
            imm = random.randint(1, 100)
            ops.append(f"addi t1, t2, {imm}")
    
    return ops

# ============================================================================
# 2. TEST-FUNKTIONS-TEMPLATE (FESTES FORMAT)
# ============================================================================

TEST_TEMPLATE = """uint32_t {name}(void) {{
    uint32_t start, end;
    uint32_t t1_val = 0x12345678;
    uint32_t t2_val = 0x87654321;
    uint32_t t3_val = 0xABCDEF01;
    uint32_t t4_val = 0xFEDCBA98;
    uint32_t t5_val = 0x13579BDF;
    uint32_t t6_val = 0x2468ACE0;
    
    portENTER_CRITICAL(&test_mutex);
    __asm__ __volatile__ (
        "fence\\n"
        "csrr %0, 0x7E2\\n"
{asm_ops}
        "csrr %1, 0x7E2\\n"
        "fence\\n"
        : "=r"(start), "=r"(end)
        : // keine Inputs nötig
        : "t1", "t2", "t3", "t4", "t5", "t6", "memory"
    );
    portEXIT_CRITICAL(&test_mutex);
    
    return end - start;
}}
"""

# ============================================================================
# 3. HEADER UND C-DATEI GENERIEREN
# ============================================================================

def generate_working_test_suite(output_dir="working_tests"):
    """Generiert eine garantiert kompilierende Test-Suite."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Header-Datei
    header = """#ifndef WORKING_TESTS_H
#define WORKING_TESTS_H

#include <stdint.h>
#include "freertos/portmacro.h"

extern portMUX_TYPE test_mutex;
void init_performance_counters(void);

// Test-Funktionen
uint32_t test_alu_chain_10ops(void);
uint32_t test_alu_chain_20ops(void);
uint32_t test_mixed_ops_15ops(void);
uint32_t test_dependency_chain(void);
uint32_t test_register_rotation(void);

void run_all_working_tests(void);
void print_working_results(void);

#endif // WORKING_TESTS_H
"""
    
    # C-Datei beginnt hier
    c_file = """#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "working_tests.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

void init_performance_counters(void) {
    __asm__ __volatile__ ("li t0, 1\\n csrw 0x7E0, t0\\n csrw 0x7E1, t0\\n" ::: "t0");
}

"""
    
    # ============================================================================
    # FESTE TEST-FUNKTIONEN (garantiert kompilierend)
    # ============================================================================
    
    # Test 1: Einfache ALU-Kette
    asm_ops1 = []
    for i in range(10):
        asm_ops1.append(f'        "add t1, t2, t3\\n"')
        asm_ops1.append(f'        "sub t4, t5, t6\\n"')
    
    test1 = TEST_TEMPLATE.format(
        name="test_alu_chain_10ops",
        asm_ops="\n".join(asm_ops1)
    )
    c_file += test1
    
    # Test 2: Längere ALU-Kette
    asm_ops2 = []
    for i in range(20):
        op = "add" if i % 2 == 0 else "sub"
        asm_ops2.append(f'        "{op} t{i%3+1}, t{(i+1)%3+1}, t{(i+2)%3+1}\\n"')
    
    test2 = TEST_TEMPLATE.format(
        name="test_alu_chain_20ops",
        asm_ops="\n".join(asm_ops2)
    )
    c_file += test2
    
    # Test 3: Gemischte Operationen
    asm_ops3 = []
    for i in range(15):
        if i % 4 == 0:
            asm_ops3.append(f'        "add t1, t2, t3\\n"')
        elif i % 4 == 1:
            asm_ops3.append(f'        "and t4, t5, t6\\n"')
        elif i % 4 == 2:
            asm_ops3.append(f'        "or t2, t3, t4\\n"')
        else:
            asm_ops3.append(f'        "xor t5, t6, t1\\n"')
    
    test3 = TEST_TEMPLATE.format(
        name="test_mixed_ops_15ops",
        asm_ops="\n".join(asm_ops3)
    )
    c_file += test3
    
    # Test 4: Dependency Chain
    asm_ops4 = []
    for i in range(12):
        asm_ops4.append(f'        "add t1, t1, t2\\n"')
        asm_ops4.append(f'        "add t2, t2, t3\\n"')
    
    test4 = TEST_TEMPLATE.format(
        name="test_dependency_chain",
        asm_ops="\n".join(asm_ops4)
    )
    c_file += test4
    
    # Test 5: Register Rotation
    asm_ops5 = []
    for i in range(8):
        asm_ops5.append(f'        "add t1, t2, t3\\n"')
        asm_ops5.append(f'        "sub t4, t1, t5\\n"')
        asm_ops5.append(f'        "and t6, t4, t2\\n"')
        asm_ops5.append(f'        "or t3, t6, t1\\n"')
    
    test5 = TEST_TEMPLATE.format(
        name="test_register_rotation",
        asm_ops="\n".join(asm_ops5)
    )
    c_file += test5
    
    # ============================================================================
    # TEST-RUNNER
    # ============================================================================
    
    c_file += """
// ============================================================================
// TEST RUNNER
// ============================================================================

typedef struct {
    const char* name;
    uint32_t (*function)(void);
    uint32_t operation_count;
    const char* description;
} working_test_t;

static const working_test_t all_working_tests[] = {
    {"alu_10", test_alu_chain_10ops, 20, "10 ALU operations chain"},
    {"alu_20", test_alu_chain_20ops, 20, "20 ALU operations chain"},
    {"mixed_15", test_mixed_ops_15ops, 15, "15 mixed operations"},
    {"dep_chain", test_dependency_chain, 24, "Dependency chain"},
    {"reg_rot", test_register_rotation, 32, "Register rotation"},
};

#define NUM_WORKING_TESTS (sizeof(all_working_tests) / sizeof(all_working_tests[0]))

void run_all_working_tests(void) {
    printf("\\n===============================================\\n");
    printf("WORKING ASSEMBLER TESTS - ESP32-C6\\n");
    printf("===============================================\\n\\n");
    
    init_performance_counters();
    vTaskDelay(pdMS_TO_TICKS(100));
    
    for (int i = 0; i < NUM_WORKING_TESTS; i++) {
        const working_test_t* test = &all_working_tests[i];
        
        uint32_t min_cycles = UINT32_MAX;
        for (int run = 0; run < 3; run++) {
            uint32_t cycles = test->function();
            if (cycles < min_cycles) min_cycles = cycles;
            vTaskDelay(pdMS_TO_TICKS(10));
        }
        
        float cpi = (float)min_cycles / test->operation_count;
        printf("%-12s: %6" PRIu32 " cycles, CPI: %5.2f - %s\\n", 
               test->name, min_cycles, cpi, test->description);
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void print_working_results(void) {
    printf("\\nCSV Output:\\n");
    printf("Test,Cycles,Operations,CPI,Description\\n");
    
    for (int i = 0; i < NUM_WORKING_TESTS; i++) {
        const working_test_t* test = &all_working_tests[i];
        uint32_t cycles = test->function();
        float cpi = (float)cycles / test->operation_count;
        printf("%s,%" PRIu32 ",%" PRIu32 ",%.2f,%s\\n",
               test->name, cycles, test->operation_count, cpi, test->description);
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
"""
    
    # ============================================================================
    # DATEIEN SCHREIBEN
    # ============================================================================
    
    with open(f"{output_dir}/working_tests.h", "w") as f:
        f.write(header)
    
    with open(f"{output_dir}/working_tests.c", "w") as f:
        f.write(c_file)
    
    # Beispiel main.c
    main_code = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "working_tests.h"

void app_main(void) {
    printf("\\nESP32-C6 Assembler Performance Tests\\n");
    printf("=====================================\\n");
    
    vTaskDelay(pdMS_TO_TICKS(2000));
    
    run_all_working_tests();
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    print_working_results();
    
    printf("\\n=== Tests Complete ===\\n");
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
"""
    
    with open(f"{output_dir}/main.c", "w") as f:
        f.write(main_code)
    
    print(f"✅ FUNKTIONIERENDE Test-Suite generiert in {output_dir}/")
    print(f"   - 5 Test-Funktionen mit je 15-32 Assembler-Operationen")
    print(f"   - Garantiert kompilierend")
    print(f"   - Viele Operationen zwischen Cycle-Counter-Lesungen")

# ============================================================================
# 4. DYNAMISCHE GENERATOR-FUNKTION (OPTIONAL)
# ============================================================================

def generate_dynamic_test(name, operation_list):
    """Generiert einen dynamischen Test (falls benötigt)."""
    asm_ops = []
    for op in operation_list:
        asm_ops.append(f'        "{op}\\\\n"')
    
    # Einfacheres Template ohne register constraints
    template = """uint32_t {name}(void) {{
    uint32_t start, end;
    
    portENTER_CRITICAL(&test_mutex);
    __asm__ __volatile__ (
        "fence\\n"
        "csrr %0, 0x7E2\\n"
{asm_ops}
        "csrr %1, 0x7E2\\n"
        "fence\\n"
        : "=r"(start), "=r"(end)
        : // keine Inputs
        : "memory"
    );
    portEXIT_CRITICAL(&test_mutex);
    
    return end - start;
}}
"""
    
    return template.format(name=name, asm_ops="\n".join(asm_ops))

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Generating guaranteed-working test suite...")
    generate_working_test_suite("working_tests")
    
    print("\n✅ Kopieren und Bauen:")
    print("  cp working_tests/working_tests.h main/")
    print("  cp working_tests/working_tests.c main/")
    print("  cp working_tests/main.c main/cycletest.c")
    print("\n  idf.py set-target esp32c6")
    print("  idf.py build")
    
    print("\n📋 Beispiel für dynamischen Test:")
    custom_ops = [
        "add t1, t2, t3",
        "sub t4, t1, t2",
        "and t5, t3, t4",
        "or t6, t5, t1",
        "xor t2, t6, t4"
    ]
    
    dyn_test = generate_dynamic_test("test_dynamic_5ops", custom_ops)
    print(dyn_test[:300] + "...")