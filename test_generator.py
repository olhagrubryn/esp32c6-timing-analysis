# test_generator.py - Einfacher Test
import subprocess
import os

# 1. Test-Verzeichnis erstellen
test_dir = "test_benchmarks"
os.makedirs(test_dir, exist_ok=True)

# 2. Einfachen Testcode generieren
test_code = """
#include <stdio.h>
#include <inttypes.h>

void test_add(void) {
    uint32_t start, end, a = 1, b = 2, c;
    
    // Performance Counter lesen
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(start));
    
    // 10x ADD
    for (int i = 0; i < 10; i++) {
        __asm__ __volatile__("add %0, %1, %2" : "=r"(c) : "r"(a), "r"(b));
    }
    
    __asm__ __volatile__("csrr %0, 0x7E2" : "=r"(end));
    
    printf("ADD test: %u cycles total, %u per instruction\\n", 
           end - start, (end - start) / 10);
}

void app_main(void) {
    printf("Generator Test\\n");
    test_add();
}
"""

# Datei schreiben
with open(f"{test_dir}/test_main.c", "w") as f:
    f.write(test_code)

print(f"Test-Code generiert in {test_dir}/")