#!/usr/bin/env python3
# scripts/generate_throughput_tests.py - ESP32-C6 Instruction Throughput Test Generator
# BASIEREND AUF: Intel Definition of Throughput (Kategorien aus Skript 1)
# FILE STRUCTURE: Verbesserte Struktur aus Skript 2

import os
import sys
import random
from collections import defaultdict

# ============================================================================
# Pfad-Konfiguration
# ============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MAIN_DIR = os.path.join(PROJECT_ROOT, "main")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

# ============================================================================
# RISC-V REGISTER (wie Skript 1, aber mit rotate_register aus Skript 2)
# ============================================================================

class RISCVRegisters:
    """Definiert gültige Register für ESP32-C6."""
    
    TEMP_REGS = ["a2", "a4", "a5", "a6", "a7"]
    BASE_REG = "a3"  # Basisregister für Speicherzugriffe - NIEMALS überschreiben!
    DST_REGS = ["a2", "a4", "a5", "a6", "a7"]
    SRC_REGS = ["a2", "a4", "a5", "a6", "a7"]
    
    @staticmethod
    def get_independent_registers(count):
        """Generiert unabhängige Register (keine RAW-Dependencies)."""
        regs = RISCVRegisters.TEMP_REGS[:]
        if count <= len(regs):
            return regs[:count]
        return [regs[i % len(regs)] for i in range(count)]
    
    @staticmethod
    def rotate_register(base_reg, offset):
        """Rotiert Register für Throughput-Tests."""
        regs = RISCVRegisters.TEMP_REGS
        if base_reg in regs:
            idx = regs.index(base_reg)
            return regs[(idx + offset) % len(regs)]
        return base_reg

# ============================================================================
# RISC-V INSTRUKTIONEN (wie Skript 1)
# ============================================================================

class RISCVInstructions:
    """Datenbank aller RISC-V Instruktionen."""
    
    @staticmethod
    def get_all_instructions():
        return {
            "add":  "add {dst}, {src1}, {src2}",
            "sub":  "sub {dst}, {src1}, {src2}",
            "xor":  "xor {dst}, {src1}, {src2}",
            "or":   "or {dst}, {src1}, {src2}",
            "and":  "and {dst}, {src1}, {src2}",
            "addi": "addi {dst}, {src1}, {imm}",
            "lw":   "lw {dst}, {offset}({base})",
            "sw":   "sw {src}, {offset}({base})",
            "mul":  "mul {dst}, {src1}, {src2}",
            "div":  "div {dst}, {src1}, {src2}",
        }
    
    @staticmethod
    def get_throughput_characteristic(insn_name):
        """
        Gibt die Durchsatz-Charakteristik einer Instruktion zurück (aus Skript 1).
        """
        characteristics = {
            "add": "THROUGHPUT_SINGLE_ISSUE",
            "sub": "THROUGHPUT_SINGLE_ISSUE",
            "xor": "THROUGHPUT_SINGLE_ISSUE",
            "or": "THROUGHPUT_SINGLE_ISSUE",
            "and": "THROUGHPUT_SINGLE_ISSUE",
            "addi": "THROUGHPUT_SINGLE_ISSUE",
            "lw": "THROUGHPUT_MEMORY",
            "sw": "THROUGHPUT_MEMORY",
            "mul": "THROUGHPUT_MULTI_CYCLE",
            "div": "THROUGHPUT_MULTI_CYCLE",
        }
        return characteristics.get(insn_name, "THROUGHPUT_SINGLE_ISSUE")

# ============================================================================
# INTEL THROUGHPUT TESTS (aus Skript 1)
# ============================================================================

class IntelThroughputGenerator:
    """
    Generiert Throughput-Tests nach Intel-Definition (aus Skript 1).
    """
    
    @staticmethod
    def generate_throughput_test(insn_name, insn_template):
        """Generiert Throughput-Test für eine Instruktion."""
        tests = []
        
        instance_counts = [4, 8, 16]
        throughput_cat = RISCVInstructions.get_throughput_characteristic(insn_name)
        
        iterations = {
            "THROUGHPUT_SINGLE_ISSUE": 5000,
            "THROUGHPUT_MEMORY": 4000,
            "THROUGHPUT_MULTI_CYCLE": 2000,
        }.get(throughput_cat, 3000)
        
        for count in instance_counts:
            registers = RISCVRegisters.get_independent_registers(count)
            instructions = []
            
            for i in range(count):
                dst = registers[i % len(registers)]
                
                if insn_name in ["lw", "sw"]:
                    # Sicherer Offset: Nur innerhalb des 64-Byte Buffers (0-60) in 4-Byte Schritten
                    offset = (i * 4) % 60
                    if insn_name == "lw":
                        instr = f"lw {dst}, {offset}({RISCVRegisters.BASE_REG})"
                    else:
                        instr = f"sw {dst}, {offset}({RISCVRegisters.BASE_REG})"
                elif insn_name == "addi":
                    src1 = registers[(i + 1) % len(registers)]
                    instr = f"addi {dst}, {src1}, 1"
                else:
                    src1 = registers[(i + 1) % len(registers)]
                    src2 = registers[(i + 2) % len(registers)]
                    instr = insn_template.format(dst=dst, src1=src1, src2=src2)
                
                instructions.append((insn_name, instr))
            
            test = {
                "name": f"THROUGHPUT_{insn_name}_{count}",
                "instructions": instructions,
                "iterations": max(1, iterations // count),
                "description": f"{count}x {insn_name} (unabhängig)",
                "category": throughput_cat,
                "instruction_count": count,
                "sequence_length": count,
                "group": "throughput_base"
            }
            tests.append(test)
        
        return tests
    
    @staticmethod
    def generate_port_conflict_test(insn_name, insn_template):
        """Spezieller Test für Port-Konflikte (aus Skript 1)."""
        tests = []
        
        for count in [4, 8]:
            registers = RISCVRegisters.get_independent_registers(count)
            instructions = []
            
            for i in range(count):
                dst = registers[i % len(registers)]
                
                if insn_name == "add":
                    src1 = registers[(i + 1) % len(registers)]
                    src2 = registers[(i + 2) % len(registers)]
                    instr = f"add {dst}, {src1}, {src2}"
                elif insn_name == "mul":
                    src1 = registers[(i + 1) % len(registers)]
                    src2 = registers[(i + 2) % len(registers)]
                    instr = f"mul {dst}, {src1}, {src2}"
                else:
                    continue
                
                instructions.append((insn_name, instr))
            
            if instructions:
                test = {
                    "name": f"PORT_CONFLICT_{insn_name}_{count}",
                    "instructions": instructions,
                    "iterations": max(1, 2000 // count),
                    "description": f"Port conflict: {count}x {insn_name}",
                    "category": "THROUGHPUT_PORT_CONFLICT",
                    "instruction_count": count,
                    "sequence_length": count,
                    "group": "throughput_port"
                }
                tests.append(test)
        
        return tests

# ============================================================================
# DEPENDENCY COMPARISON TESTS (aus Skript 1) - VOLLSTÄNDIG KORRIGIERT
# ============================================================================

class ThroughputComparisonGenerator:
    """Vergleicht dependency-free vs dependent throughput (aus Skript 1)."""
    
    @staticmethod
    def generate_comparison_tests():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        test_insns = ["add", "mul", "lw"]
        
        for insn_name in test_insns:
            template = all_insn[insn_name]
            
            # Dependency-Free
            for count in [4, 8]:
                registers = RISCVRegisters.get_independent_registers(count)
                instructions = []
                
                for i in range(count):
                    dst = registers[i % len(registers)]
                    
                    if insn_name == "lw":
                        # Sicherer Offset: 0-60 in 4-Byte Schritten
                        offset = (i * 4) % 60
                        instr = f"lw {dst}, {offset}({RISCVRegisters.BASE_REG})"
                    else:
                        src1 = registers[(i + 1) % len(registers)]
                        src2 = registers[(i + 2) % len(registers)]
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                    
                    instructions.append((insn_name, instr))
                
                test = {
                    "name": f"DEP_FREE_{insn_name}_{count}",
                    "instructions": instructions,
                    "iterations": max(1, 3000 // count),
                    "description": f"Dependency-free: {count}x {insn_name}",
                    "category": "THROUGHPUT_DEPENDENCY_FREE",
                    "instruction_count": count,
                    "sequence_length": count,
                    "group": "throughput_dependency"
                }
                tests.append(test)
            
            # Dependent (RAW chain) - KOMPLETT ÜBERARBEITET
            for count in [4, 8]:
                instructions = []
                
                if insn_name == "lw":
                    # Für Loads: KEINE RAW-Kette, da wir das Basisregister nicht überschreiben dürfen
                    # Stattdessen: Unabhängige Loads mit verschiedenen Destinationen
                    # Das ist der sicherste Ansatz für Load-Tests
                    for i in range(count):
                        dst = RISCVRegisters.TEMP_REGS[i % len(RISCVRegisters.TEMP_REGS)]
                        offset = (i * 8) % 56  # Genug Abstand zwischen den Loads
                        instr = f"lw {dst}, {offset}({RISCVRegisters.BASE_REG})"
                        instructions.append((insn_name, instr))
                else:
                    # Für ALU-Operationen: Echte RAW-Kette
                    last_dst = "a2"
                    for i in range(count):
                        dst = RISCVRegisters.TEMP_REGS[i % len(RISCVRegisters.TEMP_REGS)]
                        src1 = last_dst
                        src2 = RISCVRegisters.TEMP_REGS[(i + 2) % len(RISCVRegisters.TEMP_REGS)]
                        instr = template.format(dst=dst, src1=src1, src2=src2)
                        instructions.append((insn_name, instr))
                        last_dst = dst
                
                test = {
                    "name": f"DEP_RAW_{insn_name}_{count}",
                    "instructions": instructions,
                    "iterations": max(1, 3000 // count),
                    "description": f"RAW dependent: {count}x {insn_name}",
                    "category": "THROUGHPUT_DEPENDENT" if insn_name != "lw" else "THROUGHPUT_MEMORY",
                    "instruction_count": count,
                    "sequence_length": count,
                    "group": "throughput_dependency"
                }
                tests.append(test)
        
        return tests

# ============================================================================
# BACK-TO-BACK TESTS (aus Skript 1)
# ============================================================================

class BackToBackGenerator:
    """Testet Back-to-Back Issue Rate (aus Skript 1)."""
    
    @staticmethod
    def generate_back_to_back_tests():
        tests = []
        all_insn = RISCVInstructions.get_all_instructions()
        
        sequences = [
            (["add", "add", "add", "add"], "ADD_ONLY"),
            (["lw", "add", "lw", "add"], "LOAD_ALU_MIX"),
            (["mul", "add", "mul", "add"], "MUL_ALU_MIX"),
        ]
        
        for seq, name in sequences:
            for repeat in [2, 4]:
                instructions = []
                count = len(seq) * repeat
                registers = RISCVRegisters.get_independent_registers(count)
                
                for i in range(count):
                    insn = seq[i % len(seq)]
                    dst = registers[i % len(registers)]
                    
                    if insn == "lw":
                        # Sicherer Offset für Loads
                        offset = (i * 4) % 60
                        instr = f"lw {dst}, {offset}({RISCVRegisters.BASE_REG})"
                    elif insn == "add":
                        src1 = registers[(i + 1) % len(registers)]
                        src2 = registers[(i + 2) % len(registers)]
                        instr = f"add {dst}, {src1}, {src2}"
                    elif insn == "mul":
                        src1 = registers[(i + 1) % len(registers)]
                        src2 = registers[(i + 2) % len(registers)]
                        instr = f"mul {dst}, {src1}, {src2}"
                    else:
                        continue
                    
                    instructions.append((insn, instr))
                
                test = {
                    "name": f"BACK2BACK_{name}_{count}",
                    "instructions": instructions,
                    "iterations": max(1, 2000 // count),
                    "description": f"Back-to-back: {name} ({count} ops)",
                    "category": "THROUGHPUT_BACK_TO_BACK",
                    "instruction_count": count,
                    "sequence_length": count,
                    "group": "throughput_back2back"
                }
                tests.append(test)
        
        return tests

# ============================================================================
# C CODE GENERATOR (aus Skript 2, aber mit CPI statt Cycles/Gap)
# ============================================================================

def generate_test_function(test):
    """Generiert C-Code für Throughput-Test (mit CPI als Ergebnis)."""
    
    safe_name = test['name'].replace('-', '_').replace('.', '_')
    func_name = f"test_{safe_name}"
    
    instruction_lines = []
    for _, operands in test["instructions"]:
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    seq_len = test.get("sequence_length", test["instruction_count"])
    
    # Throughput-spezifischer Template (gibt CPI zurück)
    func_template = f"""float {func_name}(void) {{
    float total_cycles = 0;
    
    // Safe buffer in RAM - größer und mit definierten Werten
    static uint32_t safe_buffer[256] __attribute__((aligned(64))) = {{ 0 }};  // Mit Nullen initialisiert
    
    // Buffer mit definierten Werten füllen
    for (int i = 0; i < 256; i += 4) {{
        safe_buffer[i] = 0x11111111;
        safe_buffer[i+1] = 0x22222222;
        safe_buffer[i+2] = 0x33333333;
        safe_buffer[i+3] = 0x44444444;
    }}
    
    uint32_t *ptr = safe_buffer;
    
    // Initial values for registers
    uint32_t r2_val = 0x12345678;
    uint32_t r4_val = 0xABCDEF01;
    uint32_t r5_val = 0xFEDCBA98;
    uint32_t r6_val = 0x0F0F0F0F;
    uint32_t r7_val = 0xF0F0F0F0;
    
    portENTER_CRITICAL(&test_mutex);
    
    for (int iter = 0; iter < {test["iterations"]}; iter++) {{
        uint32_t t_start, t_end;
        __asm__ __volatile__ (
            "mv a3, %[mem_ptr]\\n"      // a3 = gültiger Speicherpointer (NIEMALS überschreiben!)
            "mv a2, %[r2_val]\\n"
            "mv a4, %[r4_val]\\n"
            "mv a5, %[r5_val]\\n"
            "mv a6, %[r6_val]\\n"
            "mv a7, %[r7_val]\\n"
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n" // Start cycle count
            
{instruction_block}
            
            "csrr %[t_end], 0x7E2\\n"   // End cycle count
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : [mem_ptr] "r"(ptr),
              [r2_val] "r"(r2_val),
              [r4_val] "r"(r4_val),
              [r5_val] "r"(r5_val),
              [r6_val] "r"(r6_val),
              [r7_val] "r"(r7_val)
            : "a2", "a3", "a4", "a5", "a6", "a7", "memory"
        );
        total_cycles += (float)(t_end - t_start);
    }}
    
    portEXIT_CRITICAL(&test_mutex);
    
    // Return CYCLES PER INSTRUCTION (CPI) - Intel Definition
    return total_cycles / (float)({test["iterations"]} * {test["instruction_count"]});
}}
"""
    return func_name, func_template

# ============================================================================
# FILE GENERATOR (aus Skript 2)
# ============================================================================

def ensure_directories():
    """Stellt sicher, dass alle benötigten Verzeichnisse existieren."""
    os.makedirs(MAIN_DIR, exist_ok=True)
    os.makedirs(TESTS_DIR, exist_ok=True)
    
    os.makedirs(os.path.join(TESTS_DIR, "throughput"), exist_ok=True)
    print(f"  ✓ Created throughput test directories")

def generate_test_files(all_tests):
    """Generiert alle Test-Dateien mit der Struktur aus Skript 2."""
    
    ensure_directories()
    
    test_files = []
    
    print(f"\n  Generating {len(all_tests)} throughput test files...")
    
    # Für jeden Test eine Datei generieren
    for test in all_tests:
        safe_name = test['name'].replace('-', '_').replace('.', '_')
        func_name, func_code = generate_test_function(test)
        
        # Ein gemeinsames Verzeichnis für alle Throughput-Tests
        subdir = "throughput"
        subdir_path = os.path.join(TESTS_DIR, subdir)
        
        c_filename = f"{safe_name}.c"
        h_filename = f"{safe_name}.h"
        test_path = os.path.join(subdir_path, c_filename)
        header_path = os.path.join(subdir_path, h_filename)
        
        # Header-Datei
        header_guard = f"THROUGHPUT_{safe_name.upper()}_H"
        header_content = f"""#ifndef {header_guard}
#define {header_guard}

float {func_name}(void);

#endif /* {header_guard} */
"""
        
        with open(header_path, "w") as f:
            f.write(header_content)
        
        # C-Datei
        c_content = f"""#include <stdio.h>
#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "../../main/esp32c6_throughput.h"

extern portMUX_TYPE test_mutex;

{func_code}
"""
        
        with open(test_path, "w") as f:
            f.write(c_content)
        
        test_files.append((safe_name, test, c_filename, h_filename, subdir))
        print(f"    • Generated: tests/{subdir}/{c_filename}")
    
    # Zentrale Header-Datei
    central_header = """#ifndef ESP32C6_THROUGHPUT_H
#define ESP32C6_THROUGHPUT_H

#include <stdint.h>
#include "freertos/portmacro.h"

extern portMUX_TYPE test_mutex;

// Test-Funktionen - generiert
"""
    
    for safe_name, test, _, h_file, subdir in test_files:
        central_header += f'#include "../tests/{subdir}/{h_file}"\n'
    
    central_header += """
// Initialisierung
void init_performance_counters(void);

// Test-Runner
void run_all_throughput_tests(void);
void run_throughput_category(const char* category);
void print_throughput_analysis(void);

#endif /* ESP32C6_THROUGHPUT_H */
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_throughput.h"), "w") as f:
        f.write(central_header)
    
    # Test-Runner (mit allen Tests)
    test_entries = []
    for safe_name, test, _, _, _ in test_files:
        test_entries.append(
            f'    {{"{test["name"]}", test_{safe_name}, {test["iterations"]}, '
            f'{test["instruction_count"]}, {test.get("sequence_length", test["instruction_count"])}, '
            f'"{test["description"]}", "{test["category"]}", "{test["group"]}"}}'
        )
    
    test_entries_str = ",\n".join(test_entries)
    
    # Kategorien aus Skript 1
    categories_list = [
        "THROUGHPUT_SINGLE_ISSUE",
        "THROUGHPUT_MULTI_CYCLE", 
        "THROUGHPUT_MEMORY",
        "THROUGHPUT_PORT_CONFLICT",
        "THROUGHPUT_DEPENDENCY_FREE",
        "THROUGHPUT_DEPENDENT",
        "THROUGHPUT_BACK_TO_BACK"
    ]
    
    categories_array = ",\n    ".join([f'"{cat}"' for cat in categories_list])
    
    main_content = f"""#include <stdio.h>
#include <string.h>
#include "esp32c6_throughput.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

typedef struct {{
    const char* name;
    float (*function)(void);
    int iterations;
    int instruction_count;
    int sequence_length;
    const char* description;
    const char* category;
    const char* group;
}} throughput_test_t;

static const throughput_test_t all_tests[] = {{
{test_entries_str}
}};

// Anzahl der Tests für main.c
const int NUM_TESTS = sizeof(all_tests) / sizeof(all_tests[0]);

void init_performance_counters(void) {{
    __asm__ __volatile__ (
        "li a2, 1\\n"
        "csrw 0x7E0, a2\\n"
        "csrw 0x7E1, a2\\n"
        ::: "a2"
    );
}}

void run_all_throughput_tests(void) {{
    printf("\\n========================================================\\n");
    printf("ESP32-C6 THROUGHPUT TESTS (Intel Definition)\\n");
    printf("========================================================\\n\\n");
    
    printf("%-30s %-8s %-12s %s\\n", "Test", "InstCount", "CPI", "Category");
    printf("%-30s %-8s %-12s %s\\n", "----", "--------", "---", "--------");
    
    float total_cpi = 0;
    int test_count = 0;
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        float cpi = all_tests[i].function();
        float ipc = 1.0f / cpi;
        printf("%-30s %-8d %-12.3f %s\\n", 
               all_tests[i].name, 
               all_tests[i].instruction_count,
               cpi,
               all_tests[i].category);
        total_cpi += cpi;
        test_count++;
    }}
    
    printf("\\nSummary: %d tests, average CPI = %.3f, average IPC = %.3f\\n", 
           test_count, total_cpi / test_count, 1.0f / (total_cpi / test_count));
}}

void run_throughput_category(const char* category) {{
    printf("\\nCategory: %s\\n", category);
    printf("%-30s %-8s %-12s %-10s\\n", "Test", "InstCount", "CPI", "IPC");
    printf("%-30s %-8s %-12s %-10s\\n", "----", "--------", "---", "---");
    
    float total = 0;
    int count = 0;
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].category, category) == 0) {{
            float cpi = all_tests[i].function();
            float ipc = 1.0f / cpi;
            printf("%-30s %-8d %-12.3f %-10.3f\\n", 
                   all_tests[i].name, 
                   all_tests[i].instruction_count,
                   cpi, ipc);
            total += cpi;
            count++;
        }}
    }}
    
    if (count > 0) {{
        printf("\\nAverage for %s: CPI = %.3f, IPC = %.3f\\n", 
               category, total / count, 1.0f / (total / count));
    }}
}}

void print_throughput_analysis(void) {{
    printf("\\n========================================================\\n");
    printf("THROUGHPUT ANALYSIS BY CATEGORY\\n");
    printf("========================================================\\n");
    
    const char* categories[] = {{
        {categories_array}
    }};
    
    for (int c = 0; c < {len(categories_list)}; c++) {{
        run_throughput_category(categories[c]);
    }}
}}
"""
    
    with open(os.path.join(MAIN_DIR, "esp32c6_throughput.c"), "w") as f:
        f.write(main_content)
    
    # main.c - mit extern Deklaration
    main_c = """#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_throughput.h"

// NUM_TESTS ist in esp32c6_throughput.c definiert
extern const int NUM_TESTS;

void app_main(void) {
    printf("\\n");
    printf("╔════════════════════════════════════════════════════════════╗\\n");
    printf("║     ESP32-C6 THROUGHPUT ANALYSIS (Intel Definition)       ║\\n");
    printf("║     Cycles Per Instruction (CPI) Measurement              ║\\n");
    printf("╚════════════════════════════════════════════════════════════╝\\n");
    
    vTaskDelay(pdMS_TO_TICKS(500));
    
    // Performance Counters initialisieren
    init_performance_counters();
    
    // Alle Throughput-Tests ausführen
    run_all_throughput_tests();
    
    // Detaillierte Analyse nach Kategorie
    print_throughput_analysis();
    
    printf("\\n✓ All throughput tests completed successfully!\\n");
    printf("  Total tests: %d\\n", NUM_TESTS);
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(30000));
    }
}
"""
    
    with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
        f.write(main_c)
    
    # CMakeLists.txt
    cmake_sources = "main.c\n    esp32c6_throughput.c\n"
    for safe_name, test, c_file, h_file, subdir in test_files:
        cmake_sources += f"    ../tests/{subdir}/{c_file}\n"
    
    cmake = f"""idf_component_register(SRCS {cmake_sources}
                       INCLUDE_DIRS "."
                       REQUIRES freertos)
"""
    
    with open(os.path.join(MAIN_DIR, "CMakeLists.txt"), "w") as f:
        f.write(cmake)
    
    return test_files

# ============================================================================
# MAIN GENERATOR
# ============================================================================

def main():
    """Hauptfunktion: Generiert Throughput-Test-Suite."""
    
    print("\n" + "=" * 80)
    print("                        ESP32-C6 THROUGHPUT TEST GENERATOR".center(80))
    print("                Intel Definition: Cycles Per Instruction (CPI)".center(80))
    print("=" * 80)
    
    all_insn = RISCVInstructions.get_all_instructions()
    all_tests = []
    
    # 1. Basis Throughput Tests
    print("\n[1/4] Generating base throughput tests...")
    for insn_name in all_insn:
        tests = IntelThroughputGenerator.generate_throughput_test(
            insn_name, all_insn[insn_name]
        )
        all_tests.extend(tests)
    base_count = len([t for t in all_tests if t['group'] == 'throughput_base'])
    print(f"      → {base_count} base throughput tests")
    
    # 2. Port Conflict Tests
    print("\n[2/4] Generating port conflict tests...")
    for insn_name in ["add", "mul"]:
        tests = IntelThroughputGenerator.generate_port_conflict_test(
            insn_name, all_insn[insn_name]
        )
        all_tests.extend(tests)
    port_count = len([t for t in all_tests if t['group'] == 'throughput_port'])
    print(f"      → {port_count} port conflict tests")
    
    # 3. Dependency Comparison Tests
    print("\n[3/4] Generating dependency comparison tests...")
    dep_tests = ThroughputComparisonGenerator.generate_comparison_tests()
    all_tests.extend(dep_tests)
    dep_count = len([t for t in all_tests if t['group'] == 'throughput_dependency'])
    print(f"      → {dep_count} dependency tests")
    
    # 4. Back-to-Back Tests
    print("\n[4/4] Generating back-to-back tests...")
    b2b_tests = BackToBackGenerator.generate_back_to_back_tests()
    all_tests.extend(b2b_tests)
    b2b_count = len([t for t in all_tests if t['group'] == 'throughput_back2back'])
    print(f"      → {b2b_count} back-to-back tests")
    
    # Statistiken nach Kategorie (aus Skript 1)
    print("\n" + "=" * 80)
    print("                            THROUGHPUT TEST CATEGORIES".center(80))
    print("=" * 80)
    
    categories = defaultdict(int)
    for test in all_tests:
        categories[test["category"]] += 1
    
    for cat in sorted(categories.keys()):
        print(f"  {cat}: {categories[cat]} tests")
    
    print(f"\n  TOTAL: {len(all_tests)} throughput tests")
    
    # Dateien generieren (mit Struktur aus Skript 2)
    print("\n" + "=" * 80)
    print("                           GENERATING TEST FILES".center(80))
    print("=" * 80)
    
    test_files = generate_test_files(all_tests)
    
    print("\n" + "=" * 80)
    print("                           GENERATION COMPLETE!".center(80))
    print("=" * 80)
    print("\n📁 Generated files:")
    print(f"  • {len(test_files)} test files in tests/throughput/")
    print(f"  • main/esp32c6_throughput.h")
    print(f"  • main/esp32c6_throughput.c")
    print(f"  • main/main.c")
    print(f"  • main/CMakeLists.txt")
    
    print("\n📋 NEXT STEPS:")
    print("  1. cd to project root")
    print("  2. idf.py build")
    print("  3. idf.py -p PORT flash monitor")
    print("\n   The tests measure CPI (Cycles Per Instruction)")
    print("   according to Intel definition:")
    print("   'Cycles until the same instruction can be issued again'")

if __name__ == "__main__":
    main()