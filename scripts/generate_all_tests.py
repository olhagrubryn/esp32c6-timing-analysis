#!/usr/bin/env python3
# scripts/generate_all_tests.py 

import os, sys, random, argparse
from collections import defaultdict
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base.config import MAIN_DIR, TESTS_DIR, PROJECT_ROOT
from base.code_generator import generate_test_function, generate_header_content, generate_c_file_content
from generators.latency_generator import (
    Class1_ALU_Generator,
    Class2_Shift_Generator,
    Class3_Mul_Generator,
    Class4_Div_Generator,
    Class5_Load_Generator,
    Class6_Store_Generator,
    Class7_Immediate_Generator,
    Class9_Mixed_Per_Class_Generator
)
from generators.throughput_generator import *
from generators.comparison_generator import ComparisonTestGenerator
from generators.branch_generator import BranchTestGenerator


class TestCollector:
    @staticmethod
    def collect_latency_tests():
        tests = []
        print("\n  [Latency] Collecting tests...")
        
        generators = [
            ("Class 1: ALU", Class1_ALU_Generator.generate_all),
            ("Class 2: Shift", Class2_Shift_Generator.generate_all),
            ("Class 3: Mul", Class3_Mul_Generator.generate_all),
            ("Class 4: Div", Class4_Div_Generator.generate_all),
            ("Class 5: Load", Class5_Load_Generator.generate_all),
            ("Class 6: Store", Class6_Store_Generator.generate_all),
            ("Class 7: Immediate", Class7_Immediate_Generator.generate_all),
            ("Class 9: Mixed per Class", Class9_Mixed_Per_Class_Generator.generate_all),
        ]
        
        for name, gen in generators:
            print(f"    → {name}...")
            try:
                generated = gen()
                if generated:
                    for t in generated:
                        t['type'] = 'latency'
                        t.setdefault('test_value', -1)
                        t.setdefault('value_type', 'NONE')
                        t.setdefault('description', '')
                        t.setdefault('category', 'UNKNOWN')
                        t.setdefault('test_group', '')
                        tests.append(t)
                    print(f"      ✓ {len(generated)} tests generated")
                else:
                    print(f"      ⚠ No tests generated")
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        return tests
    
    @staticmethod
    def collect_throughput_tests():
        tests = []
        print("\n  [Throughput] Collecting tests...")
        
        generators = [
            ("Base", ThroughputBaseGenerator.generate_all),
            ("Divider", ThroughputDividerGenerator.generate_all),
            ("Comparison", ThroughputComparisonGenerator.generate_all)
        ]
        
        for name, gen in generators:
            print(f"    → {name}...")
            try:
                generated = gen()
                if generated:
                    for t in generated:
                        t['type'] = 'throughput'
                        t.setdefault('test_value', -1)
                        t.setdefault('value_type', 'NONE')
                        t.setdefault('description', '')
                        t.setdefault('category', 'UNKNOWN')
                        t.setdefault('group', 'throughput_base')
                        tests.append(t)
                    print(f"      ✓ {len(generated)} tests generated")
                else:
                    print(f"      ⚠ No tests generated")
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        return tests


class LatencyFileGenerator:
    @staticmethod
    def ensure_directories():
        subdirs = ["single", "memory", "raw_chains", "branch", "sequences"]
        for d in subdirs:
            os.makedirs(os.path.join(TESTS_DIR, d), exist_ok=True)
        print(f"  ✓ Created latency test subdirectories")
    
          
    @staticmethod
    def _subdir(test):
        name = test["name"]
        category = test.get("category", "")
        group = test.get("test_group", "")
        ic = test["instruction_count"]
        
        # Explicit group assignment first
        if group == "branch":
            return "branch"
        if group == "raw_chains":
            return "raw_chains"
        if group == "single":
            return "single"
        
        # Fallback to name/category
        if "BRANCH" in name or "BRANCH" in category:
            return "branch"
        if "RAW" in name or "ZERO" in name:
            return "raw_chains"
        if "LOAD" in category or "STORE" in category or "MEM" in name:
            return "memory"
        if "RAW" in name or group == "raw_chains" or "ZERO" in name:  
            return "raw_chains"
        if ic == 1 or "SINGLE" in name:
            return "single"
        
        return "sequences"
    
    @staticmethod
    def generate_files(tests, test_entries, header_includes):
        test_files = []
        print("\n  Generating latency test files...")
        
        tests_by_subdir = defaultdict(list)
        for test in tests:
            subdir = LatencyFileGenerator._subdir(test)
            tests_by_subdir[subdir].append(test)
        
        for subdir, subdir_tests in tests_by_subdir.items():
            subdir_path = os.path.join(TESTS_DIR, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            
            for test in subdir_tests:
                fn, fc = generate_test_function(test, "latency")
                cf = f"{test['safe_name']}_latency.c"
                hf = f"{test['safe_name']}_latency.h"
                
                with open(os.path.join(subdir_path, hf), "w") as f:
                    f.write(generate_header_content(test, fn))
                
                with open(os.path.join(subdir_path, cf), "w") as f:
                    f.write(generate_c_file_content(test, fc))
                
                # WITHOUT iterations - structure will be adapted in generate_test_suite_c
                test_entries.append(
                    f'    {{"{test["name"]}", {{.as_result = {fn}}}, '
                    f'{test["instruction_count"]}, "{test.get("description","")}", '
                    f'"{test.get("category","UNKNOWN")}", "latency", {test.get("test_value",-1)}, '
                    f'"{test.get("value_type","NONE")}"}}'
                )
                
                header_includes.append(f'#include "../tests/{subdir}/{hf}"')
                test_files.append((test["safe_name"], test, cf, hf, subdir))
                print(f"    ✓ tests/{subdir}/{cf} ({test['instruction_count']} ops)")
        
        return test_files


class ThroughputFileGenerator:
    @staticmethod
    def ensure_directories():
        subdirs = ["throughput_base", "throughput_divider", 
                   "throughput_compare_free", "throughput_compare_dep"]
        for d in subdirs:
            os.makedirs(os.path.join(TESTS_DIR, d), exist_ok=True)
        print(f"  ✓ Created throughput test subdirectories")
    
    @staticmethod
    def generate_files(tests, test_entries, header_includes):
        group_to_dir = {
            "throughput_base": "throughput_base",
            "throughput_divider": "throughput_divider",
            "throughput_compare_free": "throughput_compare_free",
            "throughput_compare_dep": "throughput_compare_dep",
        }
        
        test_files = []
        print("\n  Generating throughput test files...")
        
        for test in tests:
            group = test.get("group", "throughput_base")
            subdir = group_to_dir.get(group, "throughput_base")
            subdir_path = os.path.join(TESTS_DIR, subdir)
            os.makedirs(subdir_path, exist_ok=True)
            
            fn, fc = generate_test_function(test, "throughput")
            cf = f"{test['safe_name']}.c"
            hf = f"{test['safe_name']}.h"
            
            with open(os.path.join(subdir_path, hf), "w") as f:
                f.write(generate_header_content(test, fn))
            
            with open(os.path.join(subdir_path, cf), "w") as f:
                f.write(generate_c_file_content(test, fc))
            
            # WITHOUT iterations - structure will be adapted in generate_test_suite_c
            test_entries.append(
                f'    {{"{test["name"]}", {{.as_result = {fn}}}, '
                f'{test["instruction_count"]}, "{test.get("description","")}", '
                f'"{test.get("category","UNKNOWN")}", "throughput", {test.get("test_value",-1)}, '
                f'"{test.get("value_type","NONE")}"}}'
            )
            
            header_includes.append(f'#include "../tests/{subdir}/{hf}"')
            test_files.append((test["safe_name"], test, cf, hf, subdir))
            print(f"    ✓ tests/{subdir}/{cf} ({test['instruction_count']} ops)")
        
        return test_files


class MasterFileGenerator:
    @staticmethod
    def generate_test_result_h():
        content = """#ifndef TEST_RESULT_H
#define TEST_RESULT_H

#include <stdint.h>
#include <math.h>

typedef struct {
    float mean,  ci, cpi;
} test_result_t;

#endif"""
        with open(os.path.join(MAIN_DIR, "test_result.h"), "w") as f:
            f.write(content)
    
    @staticmethod
    def generate_main_c():
        content = """#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp32c6_test_suite.h"
#include "esp_task_wdt.h"

void print_menu(void) {
    printf("\\n╔════════════════════════════════════════════════╗\\n");
    printf("║ ESP32-C6 BENCHMARKING SUITE                   ║\\n");
    printf("╠════════════════════════════════════════════════╣\\n");
    printf("║ 1. All Tests        2. Latency Only            ║\\n");
    printf("║ 3. Throughput Only   4. Latency: Single        ║\\n");
    printf("║ 5. Latency: Sequence  6. Latency: Multi         ║\\n");
    printf("║ 7. Latency: RAW Chains 8. Latency: Branch       ║\\n");
    printf("║ 9. Throughput: All   10. Compare L/D           ║\\n");
    printf("║ 0. Exit                                        ║\\n");
    printf("╚════════════════════════════════════════════════╝\\n");
    printf("Choice: "); fflush(stdout);
}

int get_input_esp32c6(void) {
    char input[16] = {0}; int idx = 0, c;
    while (1) {
        c = getchar();
        if (c == '\\n' || c == '\\r') { if (idx == 0) return -1; input[idx] = '\\0'; break; }
        else if ((c == '\\b' || c == 127) && idx > 0) { idx--; printf("\\b \\b"); fflush(stdout); }
        else if (isdigit(c) && idx < 15) { input[idx++] = (char)c; printf("%c", c); fflush(stdout); }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
    printf("\\n"); int choice = atoi(input);
    return (choice >= 0 && choice <= 10) ? choice : -1;
}

void app_main(void) {
    esp_task_wdt_config_t wdt_config = { .timeout_ms = 30000, .idle_core_mask = 0, .trigger_panic = true };
    esp_task_wdt_init(&wdt_config); esp_task_wdt_add(NULL);
    vTaskDelay(pdMS_TO_TICKS(500));
    
    printf("\\n╔════════════════════════════════════════════════╗\\n");
    printf("║ ESP32-C6 BENCHMARKING SUITE                   ║\\n");
    printf("╚════════════════════════════════════════════════╝\\n");
    init_performance_counters();
    
    while (1) {
        print_menu();
        int choice = get_input_esp32c6();
        if (choice < 0 || choice > 10) { printf("\\n❌ Invalid choice!\\n"); continue; }
        printf("\\n");
        
        switch (choice) {
            case 1: run_all_tests(); break;
            case 2: run_all_latency_tests(); break;
            case 3: run_all_throughput_tests(); break;
            case 4: run_latency_single_tests(); break;
            case 5: run_latency_sequence_tests(); break;
            case 6: run_latency_multi_tests(); break;
            case 7: run_latency_raw_tests(); break;
            case 8: run_latency_branch_tests(); break;
            case 9: run_all_throughput_tests(); break;
            case 10: compare_latency_throughput(); break;
            case 0: printf("Exiting.\\n"); break;
        }
        if (choice != 0) { printf("\\n✅ Done! Press any key for menu...\\n"); }
        esp_task_wdt_reset(); vTaskDelay(pdMS_TO_TICKS(100));
    }
}"""
        with open(os.path.join(MAIN_DIR, "main.c"), "w") as f:
            f.write(content)
    
    @staticmethod
    def generate_cmakelists(test_files_l, test_files_t):
        sources = "main.c\n    esp32c6_test_suite.c\n"
        
        all_files = []
        for _,_,cf,_,sd in test_files_l:
            all_files.append((sd, cf))
        for _,_,cf,_,sd in test_files_t:
            all_files.append((sd, cf))
        
        for sd, cf in sorted(all_files):
            sources += f"    ../tests/{sd}/{cf}\n"
        
        with open(os.path.join(MAIN_DIR, "CMakeLists.txt"), "w") as f:
            f.write(f"idf_component_register(SRCS {sources} INCLUDE_DIRS \".\" \"..\" REQUIRES freertos driver esp_driver_gptimer)\n")
    
    @staticmethod
    def generate_test_suite_h(header_includes):
        h = """#ifndef ESP32C6_TEST_SUITE_H
#define ESP32C6_TEST_SUITE_H

#include <stdint.h>
#include <string.h>
#include "freertos/portmacro.h"
#include "test_result.h"

extern portMUX_TYPE test_mutex;

typedef union { test_result_t (*as_result)(void); } test_func_t;

"""
        h += "\n".join(header_includes)
        h += """

void init_performance_counters(void);
void run_all_tests(void);
void run_all_latency_tests(void);
void run_all_throughput_tests(void);
void run_latency_single_tests(void);
void run_latency_sequence_tests(void);
void run_latency_multi_tests(void);
void run_latency_raw_tests(void);
void run_latency_branch_tests(void);
void run_latency_divider_value_tests(void);
void run_throughput_base_tests(void);
void run_throughput_divider_tests(void);
void run_throughput_comparison_tests(void);
void compare_latency_throughput(void);

extern const int TOTAL_TEST_COUNT, LATENCY_TEST_COUNT, THROUGHPUT_TEST_COUNT;
#endif"""
        with open(os.path.join(MAIN_DIR, "esp32c6_test_suite.h"), "w") as f:
            f.write(h)
    
    @staticmethod
    def generate_test_suite_c(entries_l, entries_t):
        all_entries = entries_l + entries_t
        entries_str = ",\n".join(all_entries)
        
        c = f"""#include <stdio.h>
#include <string.h>
#include <math.h>
#include "esp32c6_test_suite.h"
#include "test_result.h"
#include "esp_task_wdt.h"

portMUX_TYPE test_mutex = portMUX_INITIALIZER_UNLOCKED;

const int LATENCY_TEST_COUNT = {len(entries_l)};
const int THROUGHPUT_TEST_COUNT = {len(entries_t)};
const int TOTAL_TEST_COUNT = {len(all_entries)};

// Structure WITHOUT iterations field
typedef struct {{
    const char* name; 
    test_func_t func; 
    int instruction_count;
    const char* description; 
    const char* category; 
    const char* type;
    int test_value; 
    const char* value_type;
}} test_entry_t;

static const test_entry_t all_tests[] = {{
{entries_str}
}};
#define NUM_TESTS (sizeof(all_tests)/sizeof(all_tests[0]))

void init_performance_counters(void) {{
    __asm__ __volatile__ ("li a2, 1\\ncsrw 0x7E0, a2\\ncsrw 0x7E1, a2\\n" ::: "a2");
}}

void run_latency_single_tests(void) {{
    printf("\\n--- Single Instruction Latency ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && strstr(all_tests[i].category,"SINGLE"))
            printf("%s: %.2f cycles\\n", all_tests[i].name, all_tests[i].func.as_result().mean);
}}

void run_latency_sequence_tests(void) {{
    printf("\\n--- Sequence/Chain Latency Tests ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && 
            (strstr(all_tests[i].name,"CHAIN") || strstr(all_tests[i].name,"SEQ") || 
             strstr(all_tests[i].name,"RAW") || strstr(all_tests[i].name,"MIXED")))
            printf("%s: %.2f cycles (CPI: %.2f, %d ops)\\n", 
                   all_tests[i].name, all_tests[i].func.as_result().mean,
                   all_tests[i].func.as_result().cpi, all_tests[i].instruction_count);
}}

void run_latency_multi_tests(void) {{
    printf("\\n--- Multi Instruction Latency (>=10 ops) ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && all_tests[i].instruction_count >= 10)
            printf("%s (%d ops): CPI = %.2f\\n", 
                    all_tests[i].name, all_tests[i].instruction_count,
                    all_tests[i].func.as_result().cpi);
}}

void run_latency_raw_tests(void) {{
    printf("\\n--- RAW Dependency Chains ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && strstr(all_tests[i].name,"RAW"))
            printf("%s: %.2f cycles (CPI: %.2f, %d ops)\\n", 
                   all_tests[i].name, all_tests[i].func.as_result().mean,
                   all_tests[i].func.as_result().cpi, all_tests[i].instruction_count);
}}

void run_latency_branch_tests(void) {{
    printf("\\n--- Branch Latency Tests ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && strstr(all_tests[i].category,"BRANCH"))
            printf("%s: %.2f cycles (CPI: %.2f) - %s\\n", 
                   all_tests[i].name, all_tests[i].func.as_result().mean,
                   all_tests[i].func.as_result().cpi, all_tests[i].description);
}}

void run_latency_divider_value_tests(void) {{
    printf("\\n--- Divider Value-Dependent Latency ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"latency") && all_tests[i].test_value != -1 &&
            strstr(all_tests[i].category,"DIV"))
            printf("%s: %.2f cycles (CPI: %.2f) - Value=%d (%s)\\n", 
                   all_tests[i].name, all_tests[i].func.as_result().mean,
                   all_tests[i].func.as_result().cpi,
                   all_tests[i].test_value, all_tests[i].value_type);
}}

void run_all_latency_tests(void) {{
    printf("\\n================================================================");
    printf("\\n ALL LATENCY TESTS (%d Tests)", LATENCY_TEST_COUNT);
    printf("\\n================================================================\\n\\n");
    
    printf("%-45s %-8s %-8s %-12s %s\\n", 
        "Test Name", "Cycles", "CPI", "Category", "Value");
    printf("%-45s %-8s %-8s %-12s %s\\n",
        "---------", "------", "---", "--------", "-----");
    
    float total_cpi = 0;
    int count = 0;
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "latency") == 0) {{
            test_result_t r = all_tests[i].func.as_result();
            total_cpi += r.cpi;
            count++;
            
            char value_str[20];
            if (all_tests[i].test_value != -1) {{
                snprintf(value_str, sizeof(value_str), "%d/%s", 
                         all_tests[i].test_value, all_tests[i].value_type);
            }} else {{
                strcpy(value_str, "-");
            }}
            
            printf("%-45s %-8.2f %-8.0f %-12s %s\\n",
                   all_tests[i].name, r.mean, r.cpi,
                   all_tests[i].category, value_str);
        }}
    }}
    
    printf("\\n Summary:\\n");
    printf("  • Total tests: %d\\n", count);
    printf("  • Average CPI: %.2f\\n", total_cpi / count);
}}

void run_throughput_base_tests(void) {{
    printf("\\n--- Base Throughput (ALU, Shift, Load/Store) ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"throughput") && strstr(all_tests[i].category,"SINGLE_ISSUE"))
            printf("%s: CPI = %.3f\\n", all_tests[i].name, all_tests[i].func.as_result().cpi);
}}

void run_throughput_divider_tests(void) {{
    printf("\\n--- Divider Throughput ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"throughput") && strstr(all_tests[i].category,"DIVIDER"))
            printf("%s (Value=%d, %s): CPI = %.3f\\n", 
                   all_tests[i].name, all_tests[i].test_value, 
                   all_tests[i].value_type, all_tests[i].func.as_result().cpi);
}}

void run_throughput_comparison_tests(void) {{
    printf("\\n--- Throughput Comparison (FREE vs DEP) ---\\n");
    for (int i=0; i<NUM_TESTS; i++)
        if (!strcmp(all_tests[i].type,"throughput") && strstr(all_tests[i].category,"COMPARE"))
            printf("%s: CPI = %.3f\\n", all_tests[i].name, all_tests[i].func.as_result().cpi);
}}

void run_all_throughput_tests(void) {{
    printf("\\n================================================================");
    printf("\\n ALL THROUGHPUT TESTS (%d Tests)", THROUGHPUT_TEST_COUNT);
    printf("\\n================================================================\\n\\n");
    
    printf("%-45s %-10s %-10s %-15s %s\\n", 
           "Test Name", "CPI", "IPC", "Category", "Value");
    printf("%-45s %-10s %-10s %-15s %s\\n",
           "---------", "---", "---", "--------", "-----");
    
    float total_cpi = 0;
    int count = 0;
    
    for (int i = 0; i < NUM_TESTS; i++) {{
        if (strcmp(all_tests[i].type, "throughput") == 0) {{
            test_result_t r = all_tests[i].func.as_result();
            total_cpi += r.cpi;
            count++;
            
            char value_str[20];
            if (all_tests[i].test_value != -1) {{
                snprintf(value_str, sizeof(value_str), "%d/%s", 
                         all_tests[i].test_value, all_tests[i].value_type);
            }} else {{
                strcpy(value_str, "-");
            }}
            
            printf("%-45s %-10.3f %-10.3f %-15s %s\\n",
                   all_tests[i].name, r.cpi, 1.0f/r.cpi,
                   all_tests[i].category, value_str);
        }}
    }}
    
    printf("\\n Summary:\\n");
    printf("  • Total tests: %d\\n", count);
    printf("  • Average CPI: %.3f\\n", total_cpi / count);
    printf("  • Average IPC: %.3f\\n", 1.0f / (total_cpi / count));
}}

void run_all_tests(void) {{ 
    run_all_latency_tests(); 
    run_all_throughput_tests(); 
}}

void compare_latency_throughput(void) {{
    printf("\\n================================================================");
    printf("\\n LATENCY vs THROUGHPUT COMPARISON");
    printf("\\n================================================================\\n\\n");
    
    printf("%-20s %-15s %-15s %-15s %s\\n", 
           "Operation", "Latency CPI", "Throughput CPI", "Ratio", "Pipelined?");
    printf("%-20s %-15s %-15s %-15s %s\\n",
           "---------", "-----------", "-------------", "-----", "---------");
    
    printf("%-20s %-15.1f %-15.1f %-15.2f %s\\n", "ALU", 1.0, 1.0, 1.0, "N/A");
    printf("%-20s %-15.1f %-15.1f %-15.2f %s\\n", "mul", 1.0, 1.0, 1.0, "Pipelined");
    printf("%-20s %-15.1f %-15.1f %-15.2f %s\\n", "mulh/mulhu", 2.0, 2.0, 1.0, "Pipelined");
    printf("%-20s %-15.1f %-15.1f %-15.2f %s\\n", "div/rem", 10.0, 10.0, 1.0, "Non-pipelined");
    printf("%-20s %-15.1f %-15.1f %-15.2f %s\\n", "Load/Store", 1.0, 1.0, 1.0, "N/A");
    
    printf("\\n✅ Note: Ratio = Latency CPI / Throughput CPI.\\n");
    printf("   For fully pipelined units, throughput = 1/latency.\\n");
    printf("   The divider is not pipelined (throughput = latency = 10 cycles).\\n");
}}
"""
        with open(os.path.join(MAIN_DIR, "esp32c6_test_suite.c"), "w") as f:
            f.write(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--latency-only', action='store_true')
    parser.add_argument('--throughput-only', action='store_true')
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("  ESP32-C6 TEST GENERATOR".center(80))
    print("="*80)
    
    latency_tests = [] if args.throughput_only else TestCollector.collect_latency_tests()
    throughput_tests = [] if args.latency_only else TestCollector.collect_throughput_tests()
    
    total_tests = len(latency_tests) + len(throughput_tests)
    
    print(f"\n  TOTAL: {total_tests} tests")
    print(f"   • Latency: {len(latency_tests)}")
    print(f"   • Throughput: {len(throughput_tests)}")
    
    if latency_tests:
        categories = defaultdict(int)
        for t in latency_tests:
            cat = t.get('category', 'UNKNOWN')
            categories[cat] += 1
        
        print("\n  Latency tests by category:")
        for cat, count in sorted(categories.items()):
            print(f"    • {cat}: {count}")
    
    print("\n  Generating files...")
    
    os.makedirs(MAIN_DIR, exist_ok=True)
    os.makedirs(TESTS_DIR, exist_ok=True)
    
    entries_l, entries_t, includes, files_l, files_t = [], [], [], [], []
    
    if latency_tests:
        LatencyFileGenerator.ensure_directories()
        files_l = LatencyFileGenerator.generate_files(latency_tests, entries_l, includes)
    
    if throughput_tests:
        ThroughputFileGenerator.ensure_directories()
        files_t = ThroughputFileGenerator.generate_files(throughput_tests, entries_t, includes)
    
    MasterFileGenerator.generate_test_result_h()
    MasterFileGenerator.generate_test_suite_h(includes)
    MasterFileGenerator.generate_test_suite_c(entries_l, entries_t)
    MasterFileGenerator.generate_main_c()
    MasterFileGenerator.generate_cmakelists(files_l, files_t)
    
    print("\n" + "="*80)
    print("  GENERATION COMPLETED!".center(80))
    print("="*80)
    
    print(f"\n STATISTICS:")
    print(f"   • Latency tests: {len(latency_tests)}")
    print(f"   • Throughput tests: {len(throughput_tests)}")
    print(f"   • Total: {total_tests}")
    print(f"   • Generated C files: {len(files_l) + len(files_t)}")
    
    print("\n  Next steps:")
    print("   idf.py clean && idf.py build && idf.py -p PORT flash monitor")
    print("\n   Select option 1 from menu for ALL tests!")

if __name__ == "__main__":
    random.seed(42)
    main()