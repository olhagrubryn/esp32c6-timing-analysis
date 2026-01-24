#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/portmacro.h"
#include "performance_counter.h"

static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;

// 2. DURCHSATZ-KETTE (unabhängige ADDs) - DAS IST THROUGHPUT!
IRAM_ATTR uint32_t measure_throughput_chain(void) {
    uint32_t start, end;
    register uint32_t t1 __asm__("t1") = 1, t2 __asm__("t2") = 2, t3 __asm__("t3") = 3;
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 3\n add %2, %2, %2\n add %3, %3, %3\n add %4, %4, %4\n .endr\n"
        "add %2, %2, %2\n"
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "+r"(t1), "+r"(t2), "+r"(t3) :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}

// B. Gemischte ALU-Operationen - AUCH THROUGHPUT!
IRAM_ATTR uint32_t measure_mixed_alu_ops(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 0x12345678;
    register uint32_t b __asm__("t2") = 0x87654321;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "add %1, %1, %2\n"   // ADD
        "sub %1, %1, %2\n"   // SUB
        "xor %1, %1, %2\n"   // XOR
        "or  %1, %1, %2\n"   // OR
        "and %1, %1, %2\n"   // AND
        "sll %1, %1, %2\n"   // SLL
        "srl %1, %1, %2\n"   // SRL
        "sra %1, %1, %2\n"   // SRA
        "slt %1, %1, %2\n"   // SLT
        "sltu %1, %1, %2\n"  // SLTU
        "csrr %3, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "+r"(b), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}

// C. Branch-Penalty Test - AUCH THROUGHPUT!
IRAM_ATTR uint32_t measure_branch_penalty(void) {
    uint32_t start, end;
    register uint32_t counter __asm__("t1") = 0;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        ".rept 10\n"
        "addi %1, %1, 1\n"      // Inkrement
        "beqz %1, 1f\n"         // Branch (wird nie genommen)
        "1:\n"
        ".endr\n"
        "csrr %2, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(counter), "=r"(end)
        : 
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    return (end - start) - 1;
}