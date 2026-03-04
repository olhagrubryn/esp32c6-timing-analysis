#!/usr/bin/env python3
# scripts/base/config.py

import os

__all__ = ['SCRIPT_DIR', 'PROJECT_ROOT', 'MAIN_DIR', 'TESTS_DIR', 'TEST_TYPES']

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MAIN_DIR = os.path.join(PROJECT_ROOT, "main")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

TEST_TYPES = {
    "latency": {
        "name": "LATENCY",
        "subdirs": ["single", "chains", "sequences", "random", "stress", "memory", "multi"],
        "header": "esp32c6_latency_tests.h",
        "source": "esp32c6_latency_tests.c"
    },
    "throughput": {
        "name": "THROUGHPUT",
        "subdirs": ["throughput_base", "throughput_divider", "throughput_compare_free", "throughput_compare_dep"],
        "header": "esp32c6_throughput.h",
        "source": "esp32c6_throughput.c"
    }
}