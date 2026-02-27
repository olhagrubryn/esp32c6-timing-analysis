#!/usr/bin/env python3
# scripts/base/code_generator.py - KORRIGIERTE VERSION für Load/Store Tests

from typing import Tuple

def generate_test_function(test: dict, test_type: str = "latency") -> Tuple[str, str]:
    """
    Generiert C-Code mit optimierter Register-Nutzung.
    """
    
    func_name = f"test_{test['safe_name']}"
    
    instruction_lines = []
    for i, (insn_name, operands) in enumerate(test["instructions"]):
        if i > 0 and test_type == "latency":
            instruction_lines.append(f'            // RAW: {test["instructions"][i-1][1].split()[1]} → {operands.split()[1]}\n')
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    # Dynamische Iterationen
    base_iterations = test["iterations"]
    if "CLASS4_DIV" in test.get("category", ""):
        iterations = min(base_iterations, 100)
    elif test["instruction_count"] >= 20:
        iterations = min(base_iterations, 150)
    elif test["instruction_count"] >= 10:
        iterations = min(base_iterations, 200)
    else:
        iterations = min(base_iterations, 300)
    
    test_value = test.get("test_value", -1)
    value_type = test.get("value_type", "NONE")
    
    # Prüfe ob Load/Store Tests
    is_load_store = any(insn[0] in ['lb','lh','lw','lbu','lhu','sb','sh','sw'] 
                       for insn in test["instructions"])
    
    # Für Load/Store-Tests - SPEZIALBEHANDLUNG!
    if is_load_store:
        iterations = min(iterations, 50)  # Max 50 Iterationen für Load/Store
        if test_type == "throughput":
            return generate_throughput_loadstore_function(func_name, test, instruction_block,
                                                         iterations, test_value, value_type)
        else:
            return generate_loadstore_test_function(func_name, test, instruction_block,
                                                   iterations, test_value, value_type)
    
    # Für normale Throughput-Tests (keine Load/Store)
    if test_type == "throughput":
        return generate_throughput_test_function(func_name, test, instruction_block,
                                                iterations, test_value, value_type)
    
    # Für normale Latency-Tests
    return generate_latency_test_function(func_name, test, instruction_block,
                                         iterations, test_value, value_type)


def generate_loadstore_test_function(func_name: str, test: dict, instruction_block: str,
                                    iterations: int, test_value, value_type) -> Tuple[str, str]:
    """
    SPEZIELLE VERSION FÜR LATENCY LOAD/STORE-TESTS.
    """
    
    # Bestimme welche Register tatsächlich in den Instruktionen verwendet werden
    used_regs = set()
    for _, operands in test["instructions"]:
        parts = operands.replace(',', '').split()
        for part in parts:
            if part in ['t0','t1','t2','t3','t4','t5','t6',
                       'a0','a1','a2','a3','a4','a5','a6','a7',
                       's0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11']:
                used_regs.add(part)
    
    # Stelle sicher, dass ALLE Base-Pointer initialisiert werden!
    # Für lb t0, 0(s0) muss s0 initialisiert werden!
    
    # Clobber-Liste
    clobber_list = [f'"{reg}"' for reg in sorted(used_regs)]
    clobber_str = ', '.join(clobber_list) + ', "memory"'
    
    # Buffer mit Werten
    buffer_decl = """    
    // Safe buffer in RAM - für Load/Store Tests
    static uint32_t safe_buffer[128] __attribute__((aligned(64))) = {
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888,
        0x99999999, 0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC,
        0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678,
    };"""
    
    # Basis-Pointer - ALLE Base-Register initialisieren!
    reg_init_code = [
        '    uint32_t base_ptr = (uint32_t)safe_buffer;',
    ]
    
    # ALLE möglichen Base-Register initialisieren
    reg_init_code.append('    uint32_t s0_val = (uint32_t)safe_buffer;')
    reg_init_code.append('    uint32_t s1_val = (uint32_t)safe_buffer + 16;')
    reg_init_code.append('    uint32_t s2_val = (uint32_t)safe_buffer + 32;')
    reg_init_code.append('    uint32_t a3_val = (uint32_t)safe_buffer;')
    
    # Work-Register
    if 't0' in used_regs:
        reg_init_code.append('    uint32_t t0_val = 0x11111111;')
    if 't1' in used_regs:
        reg_init_code.append('    uint32_t t1_val = 0x22222222;')
    if 't2' in used_regs:
        reg_init_code.append('    uint32_t t2_val = 0x33333333;')
    
    # Load-Register-Code - ALLE Base-Register laden!
    load_regs_lines = [
        '            // ALLE Basis-Register laden',
        '            "mv a3, %[a3_val]\\n"',
        '            "mv s0, %[s0_val]\\n"',
        '            "mv s1, %[s1_val]\\n"',
        '            "mv s2, %[s2_val]\\n"'
    ]
    
    if 't0' in used_regs:
        load_regs_lines.append('            "mv t0, %[t0_val]\\n"')
    if 't1' in used_regs:
        load_regs_lines.append('            "mv t1, %[t1_val]\\n"')
    if 't2' in used_regs:
        load_regs_lines.append('            "mv t2, %[t2_val]\\n"')
    
    load_regs_str = '\n'.join(load_regs_lines)
    
    # Input-Liste - ALLE Werte
    input_list = [
        '[a3_val] "r"(a3_val)',
        '[s0_val] "r"(s0_val)',
        '[s1_val] "r"(s1_val)',
        '[s2_val] "r"(s2_val)'
    ]
    
    if 't0' in used_regs:
        input_list.append('[t0_val] "r"(t0_val)')
    if 't1' in used_regs:
        input_list.append('[t1_val] "r"(t1_val)')
    if 't2' in used_regs:
        input_list.append('[t2_val] "r"(t2_val)')
    
    inputs_str = ',\n            '.join(input_list)
    reg_init_str = '\n'.join(reg_init_code)
    
    # Instruction Block - OHNE zusätzliche Verarbeitung
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    // Array für alle Einzelmessungen
    uint32_t measurements[{iterations}];
    {buffer_decl}
    
    // =======================================================
    // REGISTER-INITIALISIERUNG
    // =======================================================
    
{reg_init_str}
    
    // Test-Wert: {test_value} ({value_type})
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    
    for (int iter = 0; iter < {iterations}; iter++) {{
        uint32_t t_start, t_end;
        
        // Watchdog füttern
        if (iter % 2 == 0) {{
            esp_task_wdt_reset();
        }}
        
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
{load_regs_str}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs_str}
            : {clobber_str}
        );
        
        portEXIT_CRITICAL(&test_mutex);
        
        uint32_t cycles = t_end - t_start;
        measurements[iter] = cycles;
        total_cycles += cycles;
        
        if (cycles < result.min) result.min = cycles;
        if (cycles > result.max) result.max = cycles;
    }}
    
    // =======================================================
    // STATISTISCHE BERECHNUNGEN
    // =======================================================
    
    result.mean = (float)total_cycles / {iterations};
    
    float sum_sq = 0;
    for (int i = 0; i < {iterations}; i++) {{
        float diff = measurements[i] - result.mean;
        sum_sq += diff * diff;
    }}
    result.stddev = sqrtf(sum_sq / {iterations});
    
    result.ci = 1.96 * result.stddev / sqrtf({iterations});
    result.rel_error = (result.ci / result.mean) * 100.0;
    result.cpi = result.mean / {test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template


def generate_throughput_loadstore_function(func_name: str, test: dict, instruction_block: str,
                                          iterations: int, test_value, value_type) -> Tuple[str, str]:
    """
    SPEZIELLE VERSION FÜR THROUGHPUT LOAD/STORE-TESTS.
    """
    
    # Minimale Register für Throughput Load/Store
    clobber_list = ['"t0"', '"t1"', '"t2"', '"a2"', '"a3"', '"a4"', '"a5"', '"s0"', '"memory"']
    clobber_str = ', '.join(clobber_list)
    
    # Buffer mit initialisierten Werten
    buffer_decl = """    
    // Safe buffer in RAM - für Load/Store Tests
    static uint32_t safe_buffer[128] __attribute__((aligned(64))) = {
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888,
        0x99999999, 0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC,
        0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678,
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888,
        0x99999999, 0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC,
        0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x87654321,
    };
    
    uint32_t *safe_buffer_ptr = safe_buffer;"""
    
    # Einfache Register-Initialisierung
    reg_init = f"""
    uint32_t t0_val = 0x11111111;
    uint32_t t1_val = 0x22222222;
    uint32_t t2_val = 0x33333333;
    uint32_t a2_val = 0xAAAAAAAA;
    uint32_t a4_val = 0xBBBBBBBB;
    uint32_t a5_val = 0xCCCCCCCC;
"""
    
    # Load-Register-Code - Verwende safe_buffer_ptr aus C!
    load_regs = """
            "mv t0, %[t0_val]\\n"
            "mv t1, %[t1_val]\\n"
            "mv t2, %[t2_val]\\n"
            "mv a2, %[a2_val]\\n"
            "mv a3, %[safe_ptr]\\n"      // Base-Pointer aus C-Variable!
            "mv a4, %[a4_val]\\n"
            "mv a5, %[a5_val]\\n"
            "mv s0, %[safe_ptr]\\n"       // Auch s0 als Base
"""
    
    # Input-Liste mit safe_buffer_ptr
    inputs = """[t0_val] "r"(t0_val), [t1_val] "r"(t1_val), [t2_val] "r"(t2_val),
            [a2_val] "r"(a2_val),
            [a4_val] "r"(a4_val), [a5_val] "r"(a5_val),
            [safe_ptr] "r"(safe_buffer_ptr)"""
    
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    // Array für alle Einzelmessungen
    uint32_t measurements[{iterations}];
    {buffer_decl}
    
    // =======================================================
    // REGISTER-INITIALISIERUNG
    // =======================================================
    {reg_init}
    
    // Test-Wert: {test_value} ({value_type})
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    
    for (int iter = 0; iter < {iterations}; iter++) {{
        uint32_t t_start, t_end;
        
        // Watchdog ALLE 5 Iterationen füttern
        if (iter % 5 == 0) {{
            esp_task_wdt_reset();
        }}
        
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
            // Register mit Testwerten laden
            {load_regs}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs}
            : {clobber_str}
        );
        
        portEXIT_CRITICAL(&test_mutex);
        
        uint32_t cycles = t_end - t_start;
        measurements[iter] = cycles;
        total_cycles += cycles;
        
        if (cycles < result.min) result.min = cycles;
        if (cycles > result.max) result.max = cycles;
    }}
    
    // =======================================================
    // STATISTISCHE BERECHNUNGEN
    // =======================================================
    
    result.mean = (float)total_cycles / {iterations};
    
    float sum_sq = 0;
    for (int i = 0; i < {iterations}; i++) {{
        float diff = measurements[i] - result.mean;
        sum_sq += diff * diff;
    }}
    result.stddev = sqrtf(sum_sq / {iterations});
    
    result.ci = 1.96 * result.stddev / sqrtf({iterations});
    result.rel_error = (result.ci / result.mean) * 100.0;
    result.cpi = result.mean / {test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template

def generate_latency_test_function(func_name: str, test: dict, instruction_block: str,
                                  iterations: int, test_value, value_type) -> Tuple[str, str]:
    """Generiert Code für Latency-Tests (keine Load/Store)."""
    
    # Bestimme welche Register verwendet werden
    used_regs = set()
    for _, operands in test["instructions"]:
        parts = operands.replace(',', '').split()
        for part in parts:
            if part in ['t0','t1','t2','t3','t4','t5','t6',
                       'a0','a1','a2','a3','a4','a5','a6','a7',
                       's0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11']:
                used_regs.add(part)
    
    # Für lange Ketten: Reduziere die Register
    if len(test["instructions"]) > 10:
        important_regs = {'t0', 't1', 't2', 'a2', 'a4', 'a5', 's0'}
        used_regs = used_regs.intersection(important_regs)
    
    # Clobber-Liste
    clobber_list = [f'"{reg}"' for reg in sorted(used_regs)]
    clobber_str = ', '.join(clobber_list) + ', "memory"'
    
    # Register-Initialisierung
    reg_init_code = ['    uint32_t base_ptr = 0x12345678;']
    
    reg_values = {
        't0': '0x11111111', 't1': '0x22222222', 't2': '0x33333333',
        't3': '0x44444444', 't4': '0x55555555', 't5': '0x66666666',
        't6': '0x77777777',
        'a0': '0x88888888', 'a1': '0x99999999', 'a2': '0xAAAAAAAA',
        'a4': '0xBBBBBBBB', 'a5': '0xCCCCCCCC', 'a6': '0xDDDDDDDD',
        'a7': '0xEEEEEEEE',
        's0': '0x11111111', 's1': '0x22222222', 's2': '0x33333333',
    }
    
    for reg, val in reg_values.items():
        if reg in used_regs:
            reg_init_code.append(f'    uint32_t {reg}_val = {val};')
    
    # Load-Register-Code
    load_regs_code = []
    for reg in sorted(used_regs):
        if reg in reg_values:
            load_regs_code.append(f'            "mv {reg}, %[{reg}_val]\\n"')
    
    load_regs_str = ''.join(load_regs_code)
    
    # Input-Liste
    input_list = []
    for reg in sorted(used_regs):
        if reg in reg_values:
            input_list.append(f'[{reg}_val] "r"({reg}_val)')
    
    inputs_str = ',\n            '.join(input_list) if input_list else ""
    reg_init_str = '\n'.join(reg_init_code)
    
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    // Array für alle Einzelmessungen
    uint32_t measurements[{iterations}];
    
    // =======================================================
    // REGISTER-INITIALISIERUNG
    // =======================================================
    
{reg_init_str}
    
    // Test-Wert: {test_value} ({value_type})
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    
    for (int iter = 0; iter < {iterations}; iter++) {{
        uint32_t t_start, t_end;
        
        // Watchdog alle 10 Iterationen füttern
        if (iter % 10 == 0) {{
            esp_task_wdt_reset();
        }}
        
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
            // Register mit Testwerten laden
{load_regs_str}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs_str}
            : {clobber_str}
        );
        
        portEXIT_CRITICAL(&test_mutex);
        
        uint32_t cycles = t_end - t_start;
        measurements[iter] = cycles;
        total_cycles += cycles;
        
        if (cycles < result.min) result.min = cycles;
        if (cycles > result.max) result.max = cycles;
    }}
    
    // =======================================================
    // STATISTISCHE BERECHNUNGEN
    // =======================================================
    
    result.mean = (float)total_cycles / {iterations};
    
    float sum_sq = 0;
    for (int i = 0; i < {iterations}; i++) {{
        float diff = measurements[i] - result.mean;
        sum_sq += diff * diff;
    }}
    result.stddev = sqrtf(sum_sq / {iterations});
    
    result.ci = 1.95 * result.stddev / sqrtf({iterations});
    result.rel_error = (result.ci / result.mean) * 100.0;
    result.cpi = result.mean / {test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template


def generate_throughput_test_function(func_name: str, test: dict, instruction_block: str,
                                     iterations: int, test_value, value_type) -> Tuple[str, str]:
    """
    Spezielle Version für normale Throughput-Tests (keine Load/Store).
    """
    
    # Minimale Register für Throughput
    clobber_list = ['"t0"', '"t1"', '"t2"', '"a2"', '"a4"', '"a5"', '"memory"']
    clobber_str = ', '.join(clobber_list)
    
    # Einfache Register-Initialisierung
    reg_init = """
    uint32_t t0_val = 0x11111111;
    uint32_t t1_val = 0x22222222;
    uint32_t t2_val = 0x33333333;
    uint32_t a2_val = 0xAAAAAAAA;
    uint32_t a4_val = 0xBBBBBBBB;
    uint32_t a5_val = 0xCCCCCCCC;
"""
    
    # Load-Register-Code
    load_regs = """
            "mv t0, %[t0_val]\\n"
            "mv t1, %[t1_val]\\n"
            "mv t2, %[t2_val]\\n"
            "mv a2, %[a2_val]\\n"
            "mv a4, %[a4_val]\\n"
            "mv a5, %[a5_val]\\n"
"""
    
    # Input-Liste
    inputs = """[t0_val] "r"(t0_val), [t1_val] "r"(t1_val), [t2_val] "r"(t2_val),
            [a2_val] "r"(a2_val),
            [a4_val] "r"(a4_val), [a5_val] "r"(a5_val)"""
    
    func_template = f"""#include <math.h>
#include "esp_task_wdt.h"

test_result_t {func_name}(void) {{
    test_result_t result = {{0}};
    
    // Array für alle Einzelmessungen
    uint32_t measurements[{iterations}];
    
    // =======================================================
    // REGISTER-INITIALISIERUNG
    // =======================================================
    {reg_init}
    
    // Test-Wert: {test_value} ({value_type})
    uint32_t total_cycles = 0;
    result.min = 999999999;
    result.max = 0;
    
    for (int iter = 0; iter < {iterations}; iter++) {{
        uint32_t t_start, t_end;
        
        // Watchdog alle 20 Iterationen füttern
        if (iter % 20 == 0) {{
            esp_task_wdt_reset();
        }}
        
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
            // Register mit Testwerten laden
            {load_regs}
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
            "fence\\n"
            : [t_start] "=r"(t_start), [t_end] "=r"(t_end)
            : {inputs}
            : {clobber_str}
        );
        
        portEXIT_CRITICAL(&test_mutex);
        
        uint32_t cycles = t_end - t_start;
        measurements[iter] = cycles;
        total_cycles += cycles;
        
        if (cycles < result.min) result.min = cycles;
        if (cycles > result.max) result.max = cycles;
    }}
    
    // =======================================================
    // STATISTISCHE BERECHNUNGEN
    // =======================================================
    
    result.mean = (float)total_cycles / {iterations};
    
    float sum_sq = 0;
    for (int i = 0; i < {iterations}; i++) {{
        float diff = measurements[i] - result.mean;
        sum_sq += diff * diff;
    }}
    result.stddev = sqrtf(sum_sq / {iterations});
    
    result.ci = 1.96 * result.stddev / sqrtf({iterations});
    result.rel_error = (result.ci / result.mean) * 100.0;
    result.cpi = result.mean / {test['instruction_count']};
    
    return result;
}}
"""
    return func_name, func_template

def generate_header_content(test: dict, func_name: str) -> str:
    """Generiert den Inhalt einer Header-Datei für einen Test."""
    header_guard = f"TEST_{test['safe_name'].upper()}_H"
    
    return f"""#ifndef {header_guard}
#define {header_guard}

#include "../../main/test_result.h"

test_result_t {func_name}(void);

#endif /* {header_guard} */
"""


def generate_c_file_content(test: dict, func_code: str) -> str:
    """Generiert den Inhalt einer C-Datei für einen Test."""
    return f"""#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "../../main/esp32c6_test_suite.h"
#include "../../main/test_result.h"

extern portMUX_TYPE test_mutex;

{func_code}
"""