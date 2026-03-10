#!/usr/bin/env python3
# scripts/base/test_values.py

from typing import List, Union

class TestValueRegistry:
    HIGH_THROUGHPUT_VALUES = [2, 4, 8, 16, 32, 64]
    LOW_THROUGHPUT_VALUES = [3, 7, 13, 17, 19, 23]
    EDGE_CASE_VALUES = [0, 1, 0xFFFFFFFF, 0x7FFFFFFF]
    
    @classmethod
    def get_all_values(cls) -> dict:
        return {"high": cls.HIGH_THROUGHPUT_VALUES, "low": cls.LOW_THROUGHPUT_VALUES, "edge": cls.EDGE_CASE_VALUES}
    
    @classmethod
    def get_divider_test_values(cls) -> List:
        return cls.HIGH_THROUGHPUT_VALUES + cls.LOW_THROUGHPUT_VALUES + cls.EDGE_CASE_VALUES
    
    @classmethod
    def get_value_category(cls, value: Union[int, str]) -> str:
        if value in cls.HIGH_THROUGHPUT_VALUES: return "HIGH"
        if value in cls.LOW_THROUGHPUT_VALUES: return "LOW"
        if value in cls.EDGE_CASE_VALUES: return "EDGE"
        return "UNKNOWN"