#!/usr/bin/env python3
# scripts/base/test_values.py - Gemeinsame Testwerte für Latenz & Durchsatz

from typing import Dict, List, Union

class TestValueRegistry:
    """Zentrale Registry für Testwerte - GLEICHE Werte für alle Tests!"""
    
    # High Throughput (einfache Divisionen)
    HIGH_THROUGHPUT_VALUES: List[int] = [2, 4, 8, 16, 32, 64]
    
    # Low Throughput (knifflige Divisionen)
    LOW_THROUGHPUT_VALUES: List[int] = [3, 7, 13, 17, 19, 23]
    
    # Edge Cases
    EDGE_CASE_VALUES: List[Union[int, str]] = [0, 1, 0xFFFFFFFF, 0x7FFFFFFF]
    
    @classmethod
    def get_all_values(cls) -> Dict[str, List]:
        """Alle Testwerte."""
        return {
            "high": cls.HIGH_THROUGHPUT_VALUES,
            "low": cls.LOW_THROUGHPUT_VALUES,
            "edge": cls.EDGE_CASE_VALUES
        }
    
    @classmethod
    def get_divider_test_values(cls) -> List:
        """Alle Werte für Divider-Tests."""
        return (cls.HIGH_THROUGHPUT_VALUES + 
                cls.LOW_THROUGHPUT_VALUES + 
                cls.EDGE_CASE_VALUES)
    
    @classmethod
    def get_value_category(cls, value: Union[int, str]) -> str:
        """Kategorie eines Werts."""
        if value in cls.HIGH_THROUGHPUT_VALUES:
            return "HIGH"
        elif value in cls.LOW_THROUGHPUT_VALUES:
            return "LOW"
        elif value in cls.EDGE_CASE_VALUES:
            return "EDGE"
        return "UNKNOWN"