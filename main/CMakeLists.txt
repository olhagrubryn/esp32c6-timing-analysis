# main/CMakeLists.txt
idf_component_register(SRCS "../collector.c"
                               "generated_tests/generated_tests.c"
                               "cycletest.c"
                               "latency_measurements.c"
                               "throughput_measurements.c"
                       INCLUDE_DIRS "." "generated_tests"
                       REQUIRES freertos)