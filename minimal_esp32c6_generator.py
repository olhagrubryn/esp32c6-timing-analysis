# minimal_esp32c6_generator.py
import os

# Einfaches Template
template = """
#include <stdio.h>
#include <inttypes.h>

void measure_{inst_name}(void) {{
    uint32_t start, end;
    {registers}
    
    // Counter start
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(start));
    
    // Test-Block (100 Iterationen)
    for (int i = 0; i < 100; i++) {{
        {asm_code}
    }}
    
    // Counter stop
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(end));
    
    printf("{inst_name}: %" PRIu32 " cycles\\n", end - start);
}}

void app_main(void) {{
    printf("\\nESP32-C6 Benchmarks\\n");
    measure_{inst_name}();
}}
"""

# Einfache Instruction-Liste
instructions = [
    ("add", "add t3, t1, t2", 
     "register uint32_t a = 1, b = 2, c;"),
    ("sub", "sub t3, t1, t2", 
     "register uint32_t a = 5, b = 2, c;"),
    ("and", "and t3, t1, t2", 
     "register uint32_t a = 0xF0F0, b = 0x0F0F, c;"),
]

# Dateien generieren
for inst_name, asm_code, registers in instructions:
    filename = f"{inst_name}_test.c"
    code = template.format(
        inst_name=inst_name,
        registers=registers,
        asm_code=asm_code
    )
    
    with open(filename, "w") as f:
        f.write(code)
    
    print(f"Generated: {filename}")

print("\\nCompile with:")
print("xtensa-esp32c6-elf-gcc -O0 -o test.elf test.c")