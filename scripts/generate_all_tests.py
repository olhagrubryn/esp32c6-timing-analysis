#!/usr/bin/env python3
# scripts/generate_all_tests.py - Hauptgenerator für Latenz und Durchsatz

import os
import sys
import random
import argparse
from collections import defaultdict

# Pfad für Imports setzen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Basis-Klassen
from base.config import MAIN_DIR, TESTS_DIR
from base.code_generator import generate_test_function, generate_header_content, generate_c_file_content

# Latenz-Generatoren
from generators.latency_generator import (
    SingleInstructionTestGenerator as LatencySingleGenerator,
    SequenceTestGenerator as LatencySequenceGenerator,
    MultiInstructionTestGenerator as LatencyMultiGenerator,
    LongSequenceTestGenerator as LatencyLongGenerator
)

# Durchsatz-Generatoren
from generators.throughput_generator import (
    ThroughputBaseGenerator,
    ThroughputDividerGenerator,
    ThroughputComparisonGenerator
)

# ============================================================================
# TEST-SAMMLER
# ============================================================================

class TestCollector:
    @staticmethod
    def collect_latency_tests():
        tests = []
        
        print("\n  [Latency] Single instruction tests...")
        single = LatencySingleGenerator.generate_all()
        for test in single:
            test["iterations"] = 30
        tests.extend(single)
        print(f"    → {len(single)} tests")
        
        print("  [Latency] Sequence tests...")
        seq = LatencySequenceGenerator.generate_all()
        for test in seq:
            test["iterations"] = 20
        tests.extend(seq)
        print(f"    → {len(seq)} tests")
        
        print("  [Latency] Multi instruction tests...")
        multi = LatencyMultiGenerator.generate_all()
        for test in multi:
            test["iterations"] = 10
        tests.extend(multi)
        print(f"    → {len(multi)} tests")
        
        print("  [Latency] Long sequence tests...")
        long_tests = LatencyLongGenerator.generate_all()
        for test in long_tests:
            test["iterations"] = 5
        tests.extend(long_tests)
        print(f"    → {len(long_tests)} tests")
        
        return tests
    
    @staticmethod
    def collect_throughput_tests():
        tests = []
        
        print("\n  [Throughput] Base tests...")
        base = ThroughputBaseGenerator.generate_all()
        for test in base:
            test["iterations"] = 30
        tests.extend(base)
        print(f"    → {len(base)} tests")
        
        print("  [Throughput] Divider value tests...")
        div = ThroughputDividerGenerator.generate_all()
        for test in div:
            test["iterations"] = 20
        tests.extend(div)
        print(f"    → {len(div)} tests")
        
        print("  [Throughput] Comparison tests...")
        comp = ThroughputComparisonGenerator.generate_all()
        for test in comp:
            test["iterations"] = 10
        tests.extend(comp)
        print(f"    → {len(comp)} tests")
        
        return tests

# ============================================================================
# DATEI-GENERATOR FÜR Latenz
# ============================================================================

class LatencyFileGenerator:
    """Generiert Dateien für Latenz-Tests."""
    
    @staticmethod
    def ensure_directories():
        """Erstellt benötigte Verzeichnisse."""
        subdirs = ["single", "chains", "sequences", "random", "stress", "memory", "multi"]
        for subdir in subdirs:
            os.makedirs(os.path.join(TESTS_DIR, subdir), exist_ok=True)
        print("    ✓ Latenz-Verzeichnisse erstellt")
    
    @staticmethod
    def generate_files(tests, test_entries, header_includes):
        """Generiert Latenz-Test-Dateien."""
        test_files = []
        
        for test in tests:
            # Bestimme Unterverzeichnis
            if test["instruction_count"] == 1:
                subdir = "single"
            elif test["instruction_count"] >= 20:
                subdir = "multi"
            elif "CHAIN" in test["name"]:
                subdir = "chains"
            elif "RAND" in test["name"]:
                subdir = "random"
            else:
                subdir = "sequences"
            
            subdir_path = os.path.join(TESTS_DIR, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            
            # Generiere Funktion
            func_name, func_code = generate_test_function(test, test_type="latency")
            
            # Dateinamen
            c_filename = f"{test['safe_name']}_latency.c"
            h_filename = f"{test['safe_name']}_latency.h"
            
            # Header
            header_content = generate_header_content(test, func_name)
            with open(os.path.join(subdir_path, h_filename), "w") as f:
                f.write(header_content)
            
            # C-Datei
            c_content = generate_c_file_content(test, func_code)
            with open(os.path.join(subdir_path, c_filename), "w") as f:
                f.write(c_content)
            
            # Für Test-Tabelle - Fallback für description
            description = test.get("description", f"{test['instruction_count']}x {test.get('category', 'unknown')}")
            
            test_entries.append(
                f'    {{"{test["name"]}", {func_name}, {test["iterations"]}, '
                f'{test["instruction_count"]}, "{description}", '
                f'"{test["category"]}", "latency", -1, "NONE"}}'
            )
            
            header_includes.append(f'#include "../tests/{subdir}/{h_filename}"')
            test_files.append((test["safe_name"], test, c_filename, h_filename, subdir))
            print(f"    ✓ tests/{subdir}/{c_filename}")
        
        return test_files

# ============================================================================
# DATEI-GENERATOR FÜR Durchsatz
# ============================================================================

class ThroughputFileGenerator:
    """Generiert Dateien für Durchsatz-Tests."""
    
    @staticmethod
    def ensure_directories():
        """Erstellt benötigte Verzeichnisse."""
        subdirs = ["throughput_base", "throughput_divider", "throughput_compare_free", "throughput_compare_dep"]
        for subdir in subdirs:
            os.makedirs(os.path.join(TESTS_DIR, subdir), exist_ok=True)
        print("    ✓ Durchsatz-Verzeichnisse erstellt")
    
    @staticmethod
    def generate_files(tests, test_entries, header_includes):
        """Generiert Durchsatz-Test-Dateien."""
        test_files = []
        
        group_to_dir = {
            "throughput_base": "throughput_base",
            "throughput_divider": "throughput_divider",
            "throughput_compare_free": "throughput_compare_free",
            "throughput_compare_dep": "throughput_compare_dep",
        }
        
        for test in tests:
            group = test["group"]
            subdir = group_to_dir.get(group, "throughput_base")
            subdir_path = os.path.join(TESTS_DIR, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            
            # Generiere Funktion
            func_name, func_code = generate_test_function(test, test_type="throughput")
            
            # Dateinamen
            c_filename = f"{test['safe_name']}.c"
            h_filename = f"{test['safe_name']}.h"
            
            # Header
            header_content = generate_header_content(test, func_name)
            with open(os.path.join(subdir_path, h_filename), "w") as f:
                f.write(header_content)
            
            # C-Datei
            c_content = generate_c_file_content(test, func_code)
            with open(os.path.join(subdir_path, c_filename), "w") as f:
                f.write(c_content)
            
            # Für Test-Tabelle - mit Fallback für description
            description = test.get("description", f"{test['instruction_count']}x {test.get('category', 'unknown')}")
            
            test_entries.append(
                f'    {{"{test["name"]}", {func_name}, {test["iterations"]}, '
                f'{test["instruction_count"]}, "{description}", '
                f'"{test["category"]}", "throughput", {test["test_value"]}, "{test["value_type"]}"}}'
            )
            
            header_includes.append(f'#include "../tests/{subdir}/{h_filename}"')
            test_files.append((test["safe_name"], test, c_filename, h_filename, subdir))
            print(f"    ✓ tests/{subdir}/{c_filename}")
        
        return test_files

# ============================================================================
# ZENTRALER DATEI-GENERATOR
# ============================================================================

class MasterFileGenerator:
    """Generiert alle zentralen Dateien (main.c, CMakeLists.txt, etc.)."""

    @staticmethod
    def generate_main_c():
        """Generiert main.c für ESP32-C6 - korrekte Erkennung von '10'."""
        main_c = """#include <stdio.h>
    #include <string.h>
    #include <stdlib.h>
    #include <ctype.h>
    #include "freertos/FreeRTOS.h"
    #include "freertos/task.h"
    #include "esp32c6_test_suite.h"

    void print_menu(void) {
        printf("\\n");
        printf("╔════════════════════════════════════════════════════════════╗\\n");
        printf("║     ESP32-C6 BENCHMARKING SUITE                           ║\\n");
        printf("║     Latenz + Durchsatz Analyse                            ║\\n");
        printf("╠════════════════════════════════════════════════════════════╣\\n");
        printf("║  1. Alle Tests ausführen                                  ║\\n");
        printf("║  2. Nur Latenz-Tests                                      ║\\n");
        printf("║  3. Nur Durchsatz-Tests                                   ║\\n");
        printf("║  4. Latenz: Single-Instruction Tests                      ║\\n");
        printf("║  5. Latenz: Sequenz-Tests                                 ║\\n");
        printf("║  6. Latenz: Multi-Instruction Tests                       ║\\n");
        printf("║  7. Durchsatz: Basis-Tests                                ║\\n");
        printf("║  8. Durchsatz: Divider-Wert-Tests                         ║\\n");
        printf("║  9. Durchsatz: Vergleichstests (FREE vs DEP)              ║\\n");
        printf("║ 10. Vergleich Latenz vs Durchsatz (gleiche Werte)         ║\\n");
        printf("║  0. Beenden                                               ║\\n");
        printf("╚════════════════════════════════════════════════════════════╝\\n");
        printf("Auswahl (0-10): ");
        fflush(stdout);
    }

    int get_input_esp32c6(void) {
        char input[16] = {0};  // Größerer Puffer für "10" + Newline + Null
        int index = 0;
        int c;
        
        // Zeichen für Zeichen einlesen (funktioniert zuverlässig auf ESP32-C6)
        while (1) {
            c = getchar();
            
            if (c == '\\n' || c == '\\r') {  // Enter/Return gedrückt
                if (index == 0) {
                    // Leere Eingabe - Menü wieder anzeigen
                    return -1;
                }
                input[index] = '\\0';  // String terminieren
                break;
            }
            else if (c == '\\b' || c == 127) {  // Backspace
                if (index > 0) {
                    index--;
                    printf("\\b \\b");  // Zeichen löschen
                    fflush(stdout);
                }
            }
            else if (isdigit(c) && index < (sizeof(input) - 1)) {  // Nur Ziffern
                input[index++] = (char)c;
                printf("%c", c);  // Echo
                fflush(stdout);
            }
            vTaskDelay(pdMS_TO_TICKS(5));
        }
        
        printf("\\n");  // Neue Zeile nach der Eingabe
        
        // String in Zahl konvertieren
        int choice = atoi(input);
        
        // Prüfen ob die Zahl im gültigen Bereich liegt
        if (choice >= 0 && choice <= 10) {
            return choice;
        }
        
        return -1;  // Ungültige Eingabe
    }

    void app_main(void) {
        // Kurz warten für UART Stabilität
        vTaskDelay(pdMS_TO_TICKS(500));
        
        // Performance Counter initialisieren
        init_performance_counters();
        
        int choice = -1;
        
        // Menü anzeigen
        print_menu();
        
        // Einmalige Eingabe (keine Schleife - nur ein Versuch)
        choice = get_input_esp32c6();
        
        // Prüfen ob Eingabe gültig war
        if (choice < 0 || choice > 10) {
            printf("\\n❌ Ungültige Eingabe! Starte Standard: Alle Tests (1)\\n");
            choice = 1;  // Standard: Alle Tests
        }
        
        printf("\\n");
        
        // Test ausführen
        switch (choice) {
            case 1: 
                printf("▶ Alle Tests\\n");
                run_all_tests(); 
                break;
            case 2: 
                printf("▶ Nur Latenz-Tests\\n");
                run_all_latency_tests(); 
                break;
            case 3: 
                printf("▶ Nur Durchsatz-Tests\\n");
                run_all_throughput_tests(); 
                break;
            case 4: 
                printf("▶ Latenz: Single-Instruction\\n");
                run_latency_single_tests(); 
                break;
            case 5: 
                printf("▶ Latenz: Sequenz-Tests\\n");
                run_latency_sequence_tests(); 
                break;
            case 6: 
                printf("▶ Latenz: Multi-Instruction\\n");
                run_latency_multi_tests(); 
                break;
            case 7: 
                printf("▶ Durchsatz: Basis-Tests\\n");
                run_throughput_base_tests(); 
                break;
            case 8: 
                printf("▶ Durchsatz: Divider-Wert-Tests\\n");
                run_throughput_divider_tests(); 
                break;
            case 9: 
                printf("▶ Durchsatz: Vergleichstests\\n");
                run_throughput_comparison_tests(); 
                break;
            case 10: 
                printf("▶ Vergleich Latenz vs Durchsatz\\n");
                compare_latency_throughput(); 
                break;
            case 0: 
                printf("Programm beendet.\\n");
                break;
        }
        
        if (choice != 0) {
            printf("\\n✅ Tests abgeschlossen!\\n");
            printf("Drücke Reset fuer neuen Durchlauf.\\n");
        }
        
        // Endlosschleife mit kurzen Pausen (Watchdog-freundlich)
        while (1) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }
    """
        with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
            f.write(main_c)
        print("    ✓ main.c für ESP32-C6 (erkennt '10' korrekt, nur eine Eingabe)")

    @staticmethod
    def generate_cmakelists(test_files_latency, test_files_throughput):
        """Generiert CMakeLists.txt mit allen Test-Dateien und benötigten Komponenten."""
        
        cmake_sources = "main.c\n    esp32c6_test_suite.c\n"
        
        # Latenz-Tests
        for _, _, c_file, _, subdir in test_files_latency:
            cmake_sources += f"    ../tests/{subdir}/{c_file}\n"
        
        # Durchsatz-Tests
        for _, _, c_file, _, subdir in test_files_throughput:
            cmake_sources += f"    ../tests/{subdir}/{c_file}\n"
        
        cmake = f"""idf_component_register(SRCS {cmake_sources}
                        INCLUDE_DIRS "."
                        REQUIRES freertos driver esp_driver_gptimer)
    """
        with open(os.path.join(MAIN_DIR, "CMakeLists.txt"), "w") as f:
            f.write(cmake)
        print("    ✓ CMakeLists.txt (mit esp_driver_gptimer)")
    
    @staticmethod
    def generate_test_suite_h(header_includes):
        """Generiert zentrale Header-Datei."""
        
        header = """#ifndef ESP32C6_TEST_SUITE_H
#define ESP32C6_TEST_SUITE_H

#include <stdint.h>
#include "freertos/portmacro.h"

extern portMUX_TYPE test_mutex;

// Test-Funktionen - generiert
"""
        header += "\n".join(header_includes)
        header += """

// Initialization
void init_performance_counters(void);

// Haupt-Test-Runner
void run_all_tests(void);
void run_all_latency_tests(void);
void run_all_throughput_tests(void);

// Latenz-spezifisch
void run_latency_single_tests(void);
void run_latency_sequence_tests(void);
void run_latency_multi_tests(void);

// Durchsatz-spezifisch
void run_throughput_base_tests(void);
void run_throughput_divider_tests(void);
void run_throughput_comparison_tests(void);

// Vergleich
void compare_latency_throughput(void);

// Statistiken
extern const int TOTAL_TEST_COUNT;
extern const int LATENCY_TEST_COUNT;
extern const int THROUGHPUT_TEST_COUNT;

#endif /* ESP32C6_TEST_SUITE_H */
"""
        with open(os.path.join(MAIN_DIR, "esp32c6_test_suite.h"), "w") as f:
            f.write(header)
        print("    ✓ esp32c6_test_suite.h")
    
    @staticmethod
    def generate_test_suite_c(test_entries_latency, test_entries_throughput):
        """Generiert zentrale C-Datei mit Test-Runnern."""
        
        all_entries = test_entries_latency + test_entries_throughput
        entries_str = ",\n".join(all_entries)
        
        c_content = f"""#include <stdio.h>
#include <string.h>
#include "esp32c6_test_suite.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

// Test-Statistiken
const int LATENCY_TEST_COUNT = {len(test_entries_latency)};
const int THROUGHPUT_TEST_COUNT = {len(test_entries_throughput)};
const int TOTAL_TEST_COUNT = {len(all_entries)};

// Test-Definitionen
typedef struct {{
    const char* name;
    float (*function)(void);
    int iterations;
    int instruction_count;
    const char* description;
    const char* category;
    const char* type;  // "latency" oder "throughput"
    int test_value;
    const char* value_type;
}} test_entry_t;

static const test_entry_t all_tests[] = {{
{entries_str}
}};

#define NUM_TESTS (sizeof(all_tests) / sizeof(all_tests[0]))

void init_performance_counters(void) {{
    __asm__ __volatile__ (
        "li a2, 1\\n"
        "csrw 0x7E0, a2\\n"
        "csrw 0x7E1, a2\\n"
        ::: "a2"
    );
}}

void run_all_tests(void) {{
    printf("\\n========================================================\\n");
    printf("ALLE TESTS (%d insgesamt)\\n", TOTAL_TEST_COUNT);
    printf("========================================================\\n");
    run_all_latency_tests();
    run_all_throughput_tests();
}}

void run_all_latency_tests(void) {{
    printf("\\n========================================================\\n");
    printf("LATENZ-TESTS (%d Tests)\\n", LATENCY_TEST_COUNT);
    printf("========================================================\\n");
    printf("\\n%-30s %-12s %-12s %s\\n", "Test Name", "Total Cycles", "Per Op", "Category");
    printf("%-30s %-12s %-12s %s\\n", "---------", "-----------", "------", "--------");
    
    float total = 0;
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "latency") == 0) {{
            float cycles = all_tests[i].function();
            float per_inst = cycles / (all_tests[i].iterations * all_tests[i].instruction_count);
            total += per_inst;
            printf("%-30s %-12.2f %-12.2f %s\\n", 
                   all_tests[i].name, cycles, per_inst, all_tests[i].category);
        }}
    }}
    printf("\\nAverage latency per instruction: %.2f cycles\\n", 
           total / LATENCY_TEST_COUNT);
}}

void run_all_throughput_tests(void) {{
    printf("\\n========================================================\\n");
    printf("DURCHSATZ-TESTS (%d Tests)\\n", THROUGHPUT_TEST_COUNT);
    printf("========================================================\\n");
    printf("\\n%-35s %-10s %-10s %-15s %s\\n", 
           "Test Name", "CPI", "IPC", "Category", "Value");
    printf("%-35s %-10s %-10s %-15s %s\\n",
           "---------", "---", "---", "--------", "-----");
    
    float total_cpi = 0;
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "throughput") == 0) {{
            float cpi = all_tests[i].function();
            float ipc = 1.0f / cpi;
            total_cpi += cpi;
            printf("%-35s %-10.3f %-10.3f %-15s %s %d\\n",
                   all_tests[i].name, cpi, ipc, all_tests[i].category,
                   all_tests[i].value_type, all_tests[i].test_value);
        }}
    }}
    printf("\\nAverage CPI: %.3f, Average IPC: %.3f\\n", 
           total_cpi / THROUGHPUT_TEST_COUNT, 
           (float)THROUGHPUT_TEST_COUNT / total_cpi);
}}

void run_latency_single_tests(void) {{
    printf("\\n========================================================\\n");
    printf("LATENCY Single-Instruction Tests\\n");
    printf("========================================================\\n");
    printf("%-30s %-12s %s\\n", "Test Name", "Cycles/Op", "Category");
    printf("%-30s %-12s %s\\n", "---------", "---------", "--------");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "latency") == 0 && 
            all_tests[i].instruction_count == 1) {{
            float cycles = all_tests[i].function();
            float per_inst = cycles / (all_tests[i].iterations * all_tests[i].instruction_count);
            printf("%-30s %-12.2f %s\\n", 
                   all_tests[i].name, per_inst, all_tests[i].category);
        }}
    }}
}}

void run_latency_sequence_tests(void) {{
    printf("\\n========================================================\\n");
    printf("LATENCY Sequence Tests (2-6 ops)\\n");
    printf("========================================================\\n");
    printf("%-30s %-12s %-12s %s\\n", "Test Name", "Total", "Per Op", "Category");
    printf("%-30s %-12s %-12s %s\\n", "---------", "-----", "------", "--------");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "latency") == 0 && 
            all_tests[i].instruction_count > 1 && 
            all_tests[i].instruction_count < 10) {{
            float cycles = all_tests[i].function();
            float per_inst = cycles / (all_tests[i].iterations * all_tests[i].instruction_count);
            printf("%-30s %-12.2f %-12.2f %s\\n", 
                   all_tests[i].name, cycles, per_inst, all_tests[i].category);
        }}
    }}
}}

void run_latency_multi_tests(void) {{
    printf("\\n========================================================\\n");
    printf("LATENCY Multi-Instruction Tests (10-50 ops)\\n");
    printf("========================================================\\n");
    printf("%-30s %-12s %-12s %s\\n", "Test Name", "Total", "Per Op", "Category");
    printf("%-30s %-12s %-12s %s\\n", "---------", "-----", "------", "--------");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "latency") == 0 && 
            all_tests[i].instruction_count >= 10) {{
            float cycles = all_tests[i].function();
            float per_inst = cycles / (all_tests[i].iterations * all_tests[i].instruction_count);
            printf("%-30s %-12.2f %-12.2f %s\\n", 
                   all_tests[i].name, cycles, per_inst, all_tests[i].category);
        }}
    }}
}}

void run_throughput_base_tests(void) {{
    printf("\\n========================================================\\n");
    printf("THROUGHPUT Base Tests\\n");
    printf("========================================================\\n");
    printf("%-35s %-10s %-10s %s\\n", "Test Name", "CPI", "IPC", "Category");
    printf("%-35s %-10s %-10s %s\\n", "---------", "---", "---", "--------");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "throughput") == 0 && 
            strcmp(all_tests[i].category, "THROUGHPUT_BASE") == 0) {{
            float cpi = all_tests[i].function();
            float ipc = 1.0f / cpi;
            printf("%-35s %-10.3f %-10.3f %s\\n", 
                   all_tests[i].name, cpi, ipc, all_tests[i].category);
        }}
    }}
}}

void run_throughput_divider_tests(void) {{
    printf("\\n========================================================\\n");
    printf("THROUGHPUT Divider Value Tests\\n");
    printf("========================================================\\n");
    printf("%-35s %-10s %-10s %-10s %s\\n", "Test Name", "CPI", "IPC", "Value", "Type");
    printf("%-35s %-10s %-10s %-10s %s\\n", "---------", "---", "---", "-----", "----");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "throughput") == 0 && 
            all_tests[i].test_value != -1) {{
            float cpi = all_tests[i].function();
            float ipc = 1.0f / cpi;
            printf("%-35s %-10.3f %-10.3f %-10d %s\\n", 
                   all_tests[i].name, cpi, ipc, 
                   all_tests[i].test_value, all_tests[i].value_type);
        }}
    }}
}}

void run_throughput_comparison_tests(void) {{
    printf("\\n========================================================\\n");
    printf("THROUGHPUT Comparison Tests (FREE vs DEP)\\n");
    printf("========================================================\\n");
    printf("%-35s %-10s %-10s %-15s\\n", "Test Name", "CPI", "IPC", "Type");
    printf("%-35s %-10s %-10s %-15s\\n", "---------", "---", "---", "----");
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "throughput") == 0 && 
            (strstr(all_tests[i].category, "COMPARE") != NULL)) {{
            float cpi = all_tests[i].function();
            float ipc = 1.0f / cpi;
            const char* comp_type = strstr(all_tests[i].name, "FREE") ? "FREE" : "DEP";
            printf("%-35s %-10.3f %-10.3f %-15s\\n", 
                   all_tests[i].name, cpi, ipc, comp_type);
        }}
    }}
}}

void compare_latency_throughput(void) {{
    printf("\\n========================================================\\n");
    printf("VERGLEICH: Latenz vs Durchsatz (gleiche Werte!)\\n");
    printf("========================================================\\n\\n");
    
    printf("%-10s %-15s %-15s %-15s %s\\n", 
           "Wert", "Latenz (cycles)", "Throughput (CPI)", "Ratio (L/T)", "Type");
    printf("%-10s %-15s %-15s %-15s %s\\n",
           "----", "---------------", "----------------", "-----------", "----");
    
    // Sammle alle Werte aus Durchsatz-Tests
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "throughput") == 0 && 
            all_tests[i].test_value != -1) {{
            int value = all_tests[i].test_value;
            const char* value_type = all_tests[i].value_type;
            float throughput_cpi = all_tests[i].function();
            
            printf("%-10d %-15s %-15.3f %-15s %s\\n", 
                   value, "N/A", throughput_cpi, "N/A", value_type);
        }}
    }}
    
    printf("\\nHinweis: Fuer vollstaendigen Vergleich muessen Latenz-Tests\\n");
    printf("   mit denselben Werten implementiert werden!\\n");
}}
"""
        with open(os.path.join(MAIN_DIR, "esp32c6_test_suite.c"), "w") as f:
            f.write(c_content)
        print("    ✓ esp32c6_test_suite.c")

# ============================================================================
# HAUPTFUNKTION
# ============================================================================

def main():
    """Hauptfunktion - generiert ALLE Tests."""
    
    parser = argparse.ArgumentParser(description='Generiere Latenz- und Durchsatz-Tests')
    parser.add_argument('--latency-only', action='store_true', help='Nur Latenz-Tests generieren')
    parser.add_argument('--throughput-only', action='store_true', help='Nur Durchsatz-Tests generieren')
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("  ESP32-C6 TEST GENERATOR".center(80))
    print("  Latenz + Durchsatz mit gleichen Werten!".center(80))
    print("=" * 80)
    
    # Sammle Tests
    latency_tests = []
    throughput_tests = []
    
    if not args.throughput_only:
        print("\n📊 Sammele LATENZ-Tests...")
        latency_tests = TestCollector.collect_latency_tests()
        print(f"  → {len(latency_tests)} Latenz-Tests")
    
    if not args.latency_only:
        print("\n📊 Sammele DURCHSATZ-Tests...")
        throughput_tests = TestCollector.collect_throughput_tests()
        print(f"  → {len(throughput_tests)} Durchsatz-Tests")
    
    print(f"\n📊 GESAMT: {len(latency_tests) + len(throughput_tests)} Tests")
    
    # Generiere Dateien
    print("\n📁 Generiere Test-Dateien...")
    
    # Verzeichnisse erstellen
    os.makedirs(MAIN_DIR, exist_ok=True)
    os.makedirs(TESTS_DIR, exist_ok=True)
    
    test_entries_latency = []
    test_entries_throughput = []
    header_includes = []
    test_files_latency = []
    test_files_throughput = []
    
    # Latenz-Dateien
    if latency_tests:
        print("\n  LATENZ-Testdateien:")
        LatencyFileGenerator.ensure_directories()
        test_files_latency = LatencyFileGenerator.generate_files(
            latency_tests, test_entries_latency, header_includes
        )
    
    # Durchsatz-Dateien
    if throughput_tests:
        print("\n  DURCHSATZ-Testdateien:")
        ThroughputFileGenerator.ensure_directories()
        test_files_throughput = ThroughputFileGenerator.generate_files(
            throughput_tests, test_entries_throughput, header_includes
        )
    
    # Zentrale Dateien
    print("\n  Zentrale Dateien:")
    MasterFileGenerator.generate_test_suite_h(header_includes)
    MasterFileGenerator.generate_test_suite_c(test_entries_latency, test_entries_throughput)
    MasterFileGenerator.generate_main_c()
    MasterFileGenerator.generate_cmakelists(test_files_latency, test_files_throughput)
    
    print("\n" + "=" * 80)
    print("  GENERIERUNG ABGESCHLOSSEN!".center(80))
    print("=" * 80)
    
    print(f"\n📊 STATISTIK:")
    print(f"  • Latenz-Tests: {len(latency_tests)}")
    print(f"  • Durchsatz-Tests: {len(throughput_tests)}")
    print(f"  • Gesamt: {len(latency_tests) + len(throughput_tests)}")
    print(f"\n📁 Dateien in main/ und tests/")
    print(f"\n📋 Nächste Schritte:")
    print(f"  1. idf.py build")
    print(f"  2. idf.py -p PORT flash monitor")
    print(f"  3. Im Terminal Auswahl treffen (1-10)")

if __name__ == "__main__":
    random.seed(42)
    main()