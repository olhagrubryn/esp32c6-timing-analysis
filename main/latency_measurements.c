/**
 * @file latency_measurements.c
 * @brief Complete pipeline latency measurements for ESP32-C6
 * Following uops.info methodology for all 6 categories
 */

#include <stdio.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/portmacro.h"
#include "performance_counter.h"

static portMUX_TYPE measureMux = portMUX_INITIALIZER_UNLOCKED;

// Performance Counter Initialisierung
void init_performance_counters(void) {
    __asm__ __volatile__ ("li t0, 1\n csrw 0x7E0, t0\n csrw 0x7E1, t0\n" ::: "t0");
}

// ============================================================================
// 1. DEPENDENCY CHAINS (RAW Hazards)
// ============================================================================

/**
 * @brief Simple dependency chain - measures RAW hazard penalty
 * @return Cycles per instruction in dependency chain
 */
IRAM_ATTR uint32_t measure_dependency_chain(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "add %1, %1, %1\n"
        "add %1, %1, %1\n"
        "add %1, %1, %1\n"
        "add %1, %1, %1\n"
        "csrr %2, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "=r"(end)
        :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 3;  // 3 dependencies between 4 instructions
}

// ============================================================================
// 2. REGISTER TO REGISTER LATENCY
// ============================================================================

/**
 * @brief Register-to-register ADD latency with different registers
 * @return Latency per ADD instruction
 */
IRAM_ATTR uint32_t measure_reg_to_reg_latency(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    register uint32_t b __asm__("t2") = 2;
    register uint32_t c __asm__("t3") = 3;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "add %1, %2, %3\n"    // a = b + c (no dependency on a)
        "add %2, %1, %3\n"    // b = a + c (RAW on a)
        "add %3, %1, %2\n"    // c = a + b (RAW on a, b)
        "csrr %4, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "+r"(b), "+r"(c), "=r"(end)
        :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 2;  // 2 true dependencies
}

/**
 * @brief Test move operations (RISC-V: ADD with zero register)
 * @return Latency per move operation
 */
IRAM_ATTR uint32_t measure_move_latency(void) {
    uint32_t start, end;
    register uint32_t src __asm__("t1") = 0x12345678;
    register uint32_t dst __asm__("t2") = 0;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "add %2, %1, zero\n"   // dst = src + 0
        "add %1, %2, zero\n"   // src = dst + 0
        "add %2, %1, zero\n"   // dst = src + 0
        "add %1, %2, zero\n"   // src = dst + 0
        "csrr %3, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(src), "+r"(dst), "=r"(end)
        :: "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 4;
}

// ============================================================================
// 3. MEMORY TO REGISTER (LOAD LATENCY)
// ============================================================================

/**
 * @brief Load latency from L1 cache (stack variable)
 * @return Cycles per load operation
 */
IRAM_ATTR uint32_t measure_load_latency_l1(void) {
    uint32_t start, end;
    volatile uint32_t data __attribute__((aligned(4))) = 0xDEADBEEF;
    register uint32_t result;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "lw %2, 0(%3)\n"
        "lw %2, 0(%3)\n"
        "lw %2, 0(%3)\n"
        "lw %2, 0(%3)\n"
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "=&r"(result)
        : "r"(&data)
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 4;
}

/**
 * @brief Load-use dependency chain (KORRIGIERT)
 * @return Latency for load followed by dependent operation
 */
IRAM_ATTR uint32_t measure_load_use_chain(void) {
    uint32_t start, end;
    static volatile uint32_t array[4] __attribute__((aligned(4))) = {1, 2, 3, 4};
    register uint32_t sum __asm__("t1") = 0;
    register uint32_t* arr_ptr = (uint32_t*)array;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "lw t2, 0(%3)\n"      // Load array[0]
        "add %1, %1, t2\n"    // sum += loaded value (dependent)
        "lw t2, 4(%3)\n"      // Load array[1]
        "add %1, %1, t2\n"    // sum += loaded value (dependent)
        "csrr %2, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(sum), "=r"(end)
        : "r"(arr_ptr)
        : "t2", "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 2;  // 2 load-use pairs
}

// ============================================================================
// 4. RISC-V ADAPTATION: CONDITIONAL BRANCHES (instead of Status Flags)
// ============================================================================

/**
 * @brief Conditional branch latency (RISC-V equivalent to status flags)
 * @return Cycles per conditional branch decision
 */
IRAM_ATTR uint32_t measure_branch_decision_latency(void) {
    uint32_t start, end;
    register uint32_t a __asm__("t1") = 1;
    register uint32_t b __asm__("t2") = 2;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "bne %1, %2, 1f\n"    // Branch if a != b (always taken)
        "1: addi %1, %1, 1\n" // Target
        "bne %1, %2, 1f\n"    // Another branch
        "1: addi %1, %1, 1\n"
        "csrr %3, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(a), "+r"(b), "=r"(end)
        : /* leer */
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 2;
}

// ============================================================================
// 5. REGISTER TO MEMORY (STORE LATENCY)
// ============================================================================

/**
 * @brief Store-forwarding latency test
 * @return Combined store+load latency
 */
IRAM_ATTR uint32_t measure_store_forwarding_latency(void) {
    uint32_t start, end;
    static volatile uint32_t memory __attribute__((aligned(4))) = 0;
    register uint32_t value __asm__("t1") = 0x12345678;
    register uint32_t* mem_ptr = (uint32_t*)&memory;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "sw %2, 0(%3)\n"      // Store value to memory
        "lw %2, 0(%3)\n"      // Load it back
        "sw %2, 0(%3)\n"      // Store again
        "lw %2, 0(%3)\n"      // Load again
        "csrr %1, 0x7E2\n"
        "fence\n"
        : "=r"(start), "=r"(end), "+r"(value)
        : "r"(mem_ptr)
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return (end - start) / 4;  // 4 operations total
}

// ============================================================================
// 6. DIVISIONS (VARIABLE LATENCY)
// ============================================================================

/**
 * @brief Division latency with fast inputs (power of two)
 * @return Cycles per division (optimistic case)
 */
IRAM_ATTR uint32_t measure_div_latency_fast(void) {
    uint32_t start, end;
    register uint32_t dividend __asm__("t1") = 1024;  // 2^10
    register uint32_t divisor __asm__("t2") = 2;      // Power of two
    register uint32_t quotient __asm__("t3") = 0;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "div %3, %1, %2\n"    // quotient = dividend / divisor
        "csrr %4, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(dividend), "+r"(divisor), "+r"(quotient), "=r"(end)
        : /* leer */
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return end - start;
}

/**
 * @brief Division latency with slow inputs (prime numbers)
 * @return Cycles per division (pessimistic case)
 */
IRAM_ATTR uint32_t measure_div_latency_slow(void) {
    uint32_t start, end;
    register uint32_t dividend __asm__("t1") = 1234567;  // Prime-ish
    register uint32_t divisor __asm__("t2") = 17;        // Prime
    register uint32_t quotient __asm__("t3") = 0;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr %0, 0x7E2\n"
        "div %3, %1, %2\n"    // quotient = dividend / divisor
        "csrr %4, 0x7E2\n"
        "fence\n"
        : "=r"(start), "+r"(dividend), "+r"(divisor), "+r"(quotient), "=r"(end)
        : /* leer */
        : "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    return end - start;
}

// ============================================================================
// ADDITIONAL: MEMORY HIERARCHY TESTS
// ============================================================================

/**
 * @brief Test cache vs memory latency difference
 * @return Ratio of memory latency to cache latency
 */
IRAM_ATTR void measure_memory_hierarchy(void) {
    // L1 cache access (stack)
    static volatile uint32_t l1_data = 0xAAAA;
    uint32_t l1_time = 0;
    register uint32_t temp;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr t4, 0x7E2\n"
        "lw t5, 0(%1)\n"
        "csrr %0, 0x7E2\n"
        "sub %0, %0, t4\n"
        "fence\n"
        : "=r"(l1_time), "=r"(temp)
        : "r"(&l1_data)
        : "t4", "t5", "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    // Assuming uncached access (simulated by flushing)
    uint32_t mem_time = 0;
    volatile uint32_t* uncached = (volatile uint32_t*)0x3F400000;
    
    portENTER_CRITICAL(&measureMux);
    __asm__ __volatile__ (
        "fence\n"
        "csrr t4, 0x7E2\n"
        "lw t5, 0(%1)\n"
        "csrr %0, 0x7E2\n"
        "sub %0, %0, t4\n"
        "fence\n"
        : "=r"(mem_time), "=r"(temp)
        : "r"(uncached)
        : "t4", "t5", "memory"
    );
    portEXIT_CRITICAL(&measureMux);
    
    printf("  L1 Cache: %" PRIu32 " cycles\n", l1_time);
    printf("  Memory:   %" PRIu32 " cycles\n", mem_time);
    if (l1_time > 0) {
        printf("  Ratio:    %.1fx slower\n", (float)mem_time / l1_time);
    }
}

// ============================================================================
// MAIN TEST FUNCTION
// ============================================================================

/**
 * @brief Run all 6 categories of latency measurements
 */
void run_complete_latency_analysis(void) {
    printf("\n===============================================\n");
    printf("ESP32-C6 COMPLETE LATENCY ANALYSIS (6 Categories)\n");
    printf("===============================================\n");
    
    // 1. Dependency Chains
    printf("\n1. DEPENDENCY CHAINS (RAW Hazards):\n");
    uint32_t dep = measure_dependency_chain();
    printf("  ADD chain latency: %" PRIu32 " cycles/instruction\n", dep);
    
    // 2. Register to Register
    printf("\n2. REGISTER TO REGISTER LATENCY:\n");
    uint32_t reg_reg = measure_reg_to_reg_latency();
    uint32_t move = measure_move_latency();
    printf("  ADD latency: %" PRIu32 " cycles\n", reg_reg);
    printf("  MOVE latency: %" PRIu32 " cycles\n", move);
    
    // 3. Memory to Register
    printf("\n3. MEMORY TO REGISTER (Load Latency):\n");
    uint32_t load_l1 = measure_load_latency_l1();
    uint32_t load_use = measure_load_use_chain();
    printf("  L1 Load: %" PRIu32 " cycles\n", load_l1);
    printf("  Load-Use: %" PRIu32 " cycles\n", load_use);
    
    // 4. Conditional Branches (RISC-V)
    printf("\n4. CONDITIONAL BRANCHES (RISC-V Status Flags Equivalent):\n");
    uint32_t branch = measure_branch_decision_latency();
    printf("  Branch decision: %" PRIu32 " cycles\n", branch);
    
    // 5. Register to Memory
    printf("\n5. REGISTER TO MEMORY (Store Latency):\n");
    uint32_t store_fwd = measure_store_forwarding_latency();
    printf("  Store+Load (forwarding): %" PRIu32 " cycles/pair\n", store_fwd);
    
    // 6. Divisions
    printf("\n6. DIVISIONS (Variable Latency):\n");
    uint32_t div_fast = measure_div_latency_fast();
    uint32_t div_slow = measure_div_latency_slow();
    printf("  Fast case (power of two): %" PRIu32 " cycles\n", div_fast);
    printf("  Slow case (primes): %" PRIu32 " cycles\n", div_slow);
    if (div_fast > 0) {
        printf("  Variability: %.1fx\n", (float)div_slow / div_fast);
    }
    
    // Bonus: Memory Hierarchy
    printf("\nMEMORY HIERARCHY ANALYSIS:\n");
    measure_memory_hierarchy();
    
    printf("\n===============================================\n");
    printf("Analysis Complete - All 6 uops.info categories covered\n");
    printf("===============================================\n");
}