#!/usr/bin/env python3
# scripts/generate_throughput_tests.py - Wrapper für Durchsatz-Tests

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_all_tests import main

if __name__ == "__main__":
    # Nur Durchsatz-Tests generieren
    sys.argv.append('--throughput-only')
    main()