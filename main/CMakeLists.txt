idf_component_register(
    SRCS
        "cycletest.c"
        "latency_measurements.c"
        "throughput_measurements.c"
    INCLUDE_DIRS
        "."
    REQUIRES
        freertos
        generated_tests  # Diese Zeile hinzufügen
)
