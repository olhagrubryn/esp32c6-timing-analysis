#!/usr/bin/env python3
# scripts/base/code_generator.py - Gemeinsamer C-Code Generator

from typing import Tuple

def generate_test_function(test: dict, test_type: str = "latency") -> Tuple[str, str]:
    """
    Universeller C-Code Generator - FIXED: Kritische Abschnitte minimiert!
    """
    
    func_name = f"test_{test['safe_name']}"
    
    instruction_lines = []
    for insn_name, operands in test["instructions"]:
        instruction_lines.append(f'            "{operands}\\n"')
    
    instruction_block = "".join(instruction_lines)
    
    # ITERATIONEN RADIKAL REDUZIEREN!
    base_iterations = test["iterations"]
    
    if "COMPARE" in test["name"] or test.get("type") == "latency_compare":
        iterations = min(base_iterations, 5)  # Nur 5 Iterationen für Vergleich!
    elif test["instruction_count"] >= 20:
        iterations = min(base_iterations, 3)  # Nur 3 für lange Tests
    elif test["instruction_count"] >= 10:
        iterations = min(base_iterations, 5)  # Nur 5 für Multi
    elif test["instruction_count"] >= 5:
        iterations = min(base_iterations, 10) # Nur 10 für Sequenzen
    else:
        iterations = min(base_iterations, 15) # Nur 15 für Single
    
    if test_type == "latency":
        return_statement = "return total_cycles;"
    else:
        return_statement = f"return total_cycles / (float)({iterations} * {test['instruction_count']});"
    
    test_value = test.get("test_value", -1)
    value_type = test.get("value_type", "NONE")
    
    # WICHTIG: Kritischer Abschnitt NUR um die Instruktionen, NICHT um die ganze Schleife!
    func_template = f"""float {func_name}(void) {{
    float total_cycles = 0;
    
    static uint32_t safe_buffer[64] __attribute__((aligned(64))) = {{
        0x11111111, 0x22222222, 0x33333333, 0x44444444,
        0x55555555, 0x66666666, 0x77777777, 0x88888888,
        0x99999999, 0xAAAAAAAA, 0xBBBBBBBB, 0xCCCCCCCC,
        0xDDDDDDDD, 0xEEEEEEEE, 0xFFFFFFFF, 0x12345678,
    }};
    
    uint32_t *ptr = safe_buffer;
    
    uint32_t r2_val = 0x12345678;
    uint32_t r4_val = 0xABCDEF01;
    uint32_t r5_val = 0xFEDCBA98;
    uint32_t r6_val = 0x0F0F0F0F;
    uint32_t r7_val = 0xF0F0F0F0;
    
    // Test-Wert: {test_value} ({value_type})
    
    for (int iter = 0; iter < {iterations}; iter++) {{
        uint32_t t_start, t_end;
        
        // KRITISCHER ABSCHNITT - NUR für die Messung!
        portENTER_CRITICAL(&test_mutex);
        
        __asm__ __volatile__ (
            "mv a3, %[mem_ptr]\\n"
            "mv a2, %[r2_val]\\n"
            "mv a4, %[r4_val]\\n"
            "mv a5, %[r5_val]\\n"
            "mv a6, %[r6_val]\\n"
            "mv a7, %[r7_val]\\n"
            "fence\\n"
            "csrr %[t_start], 0x7E2\\n"
{instruction_block}
            "csrr %[t_end], 0x7E2\\n"
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
        
        portEXIT_CRITICAL(&test_mutex);
        
        total_cycles += (float)(t_end - t_start);
        
        // WATCHDOG-FEED: Kurze Pause nach jeder Iteration
        if (iter % 2 == 1) {{
            for (int w = 0; w < 100; w++) {{
                __asm__ __volatile__ ("nop");
            }}
        }}
    }}
    
    {return_statement}
}}
"""
    return func_name, func_template

def generate_header_content(test: dict, func_name: str) -> str:
    header_guard = f"TEST_{test['safe_name'].upper()}_H"
    return f"""#ifndef {header_guard}
#define {header_guard}

float {func_name}(void);

#endif /* {header_guard} */
"""

def generate_c_file_content(test: dict, func_code: str) -> str:
    return f"""#include <stdio.h>
#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "../../main/esp32c6_test_suite.h"

extern portMUX_TYPE test_mutex;

{func_code}
"""