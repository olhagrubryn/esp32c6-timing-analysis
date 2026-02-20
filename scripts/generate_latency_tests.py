#!/usr/bin/env python3
# scripts/generate_latency_tests.py - Wrapper für Latenz-Tests

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_all_tests import main

if __name__ == "__main__":
    # Nur Latenz-Tests generieren
    sys.argv.append('--latency-only')
    main()