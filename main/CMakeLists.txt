# main/CMakeLists.txt
idf_component_register(SRCS "working_tests.c"
                               "main.c"
                       INCLUDE_DIRS "."
                       REQUIRES freertos)