#ifndef GENERATED_TESTS_H
#define GENERATED_TESTS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Deklaration der generierten Testfunktionen
uint32_t test_add(void);
uint32_t test_sub(void);
uint32_t test_and(void);
uint32_t test_or(void);
uint32_t test_xor(void);

// Hilfsfunktion zum Ausführen aller Tests
void run_all_generated_tests(void);

#ifdef __cplusplus
}
#endif

#endif // GENERATED_TESTS_H
