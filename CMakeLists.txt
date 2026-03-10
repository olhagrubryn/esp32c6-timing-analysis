cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(esp32c6_latency_tests)

# DIESE ZEILE LÖSCHEN - idf_component_register darf hier NICHT sein!
# idf_component_register(SRCS "esp32c6_latency_tests.c"
#                        INCLUDE_DIRS "."
#                        REQUIRES freertos)