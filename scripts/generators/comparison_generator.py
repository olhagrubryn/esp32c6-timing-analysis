#!/usr/bin/env python3
# scripts/generators/comparison_generator.py - Vergleichs-Tests Latenz vs Durchsatz

import random
from base.registers import RISCVRegisters
from base.instructions import RISCVInstructions
from base.test_values import TestValueRegistry

class ComparisonTestGenerator:
    @staticmethod
    def generate_latency_for_divider_values():
        tests = []
        
        # Nur repräsentative Werte, nicht alle!
        test_values = [2, 3, 7, 16, 32]  # Weniger Werte!
        
        for value in test_values:
            value_type = TestValueRegistry.get_value_category(value)
            
            instructions = [("div", "div a2, a4, a5")]
            
            test = {
                "name": f"LATENCY_COMPARE_DIV_{value_type}_{value}",
                "safe_name": f"latency_compare_div_{value_type}_{value}",
                "instructions": instructions,
                "iterations": 5,  # Nur 5 Iterationen!
                "instruction_count": 1,
                "description": f"Latenz DIV mit Wert {value}",
                "category": "COMPARE_LATENCY",
                "group": "compare_latency",
                "test_value": value,
                "value_type": value_type,
                "type": "latency_compare"
            }
            tests.append(test)
        
        return tests
    
    @staticmethod
    def generate_latency_for_throughput_comparison():
        tests = []
        
        # Nur 2 Werte zum Testen
        test_values = [2, 7]
        
        for value in test_values:
            value_type = TestValueRegistry.get_value_category(value)
            
            # FREE Variante
            instructions_free = [("div", "div a2, a4, a5")]
            
            test_free = {
                "name": f"LATENCY_COMPARE_FREE_{value_type}_{value}",
                "safe_name": f"latency_compare_free_{value_type}_{value}",
                "instructions": instructions_free,
                "iterations": 5,  # Nur 5!
                "instruction_count": 1,
                "description": f"FREE DIV {value}",
                "category": "COMPARE_LATENCY_FREE",
                "group": "compare_latency_free",
                "test_value": value,
                "value_type": value_type,
                "type": "latency_compare"
            }
            tests.append(test_free)
            
            # DEP Variante - KÜRZERE KETTE!
            instructions_dep = [
                ("div", "div a2, a4, a5"),
                ("div", "div a4, a2, a6")
            ]  # Nur 2 Instruktionen in der Kette!
            
            test_dep = {
                "name": f"LATENCY_COMPARE_DEP_{value_type}_{value}",
                "safe_name": f"latency_compare_dep_{value_type}_{value}",
                "instructions": instructions_dep,
                "iterations": 5,  # Nur 5!
                "instruction_count": 2,
                "description": f"DEP DIV {value}",
                "category": "COMPARE_LATENCY_DEP",
                "group": "compare_latency_dep",
                "test_value": value,
                "value_type": value_type,
                "type": "latency_compare"
            }
            tests.append(test_dep)
        
        return tests