#!/usr/bin/env python3
# scripts/base/registers.py - Gemeinsame Register-Definitionen

class RISCVRegisters:
    """Definiert gültige Register für ESP32-C6."""
    
    TEMP_REGS = ["a2", "a4", "a5", "a6", "a7"]
    BASE_REG = "a3"
    DST_REGS = ["a2", "a4", "a5", "a6", "a7"]
    SRC_REGS = ["a2", "a4", "a5", "a6", "a7"]
    
    @classmethod
    def get_independent_registers(cls, count: int) -> list:
        """Generiert unabhängige Register (für Throughput)."""
        regs = cls.TEMP_REGS[:]
        if count <= len(regs):
            return regs[:count]
        return [regs[i % len(regs)] for i in range(count)]
    
    @classmethod
    def get_register_combinations(cls) -> dict:
        """Verschiedene Register-Kombinationen für Tests."""
        return {
            "same_reg": ["a2", "a2", "a2"],
            "diff_reg": ["a2", "a4", "a5"],
            "dst_src1": ["a2", "a2", "a4"],
            "dst_src2": ["a2", "a4", "a2"],
            "src1_src2": ["a4", "a4", "a4"],
        }
    
    @classmethod
    def get_stress_registers(cls, count: int) -> list:
        """Generiert eine Liste von Registern für Stress-Tests."""
        regs = cls.TEMP_REGS[:]
        if count <= len(regs):
            return regs[:count]
        return [regs[i % len(regs)] for i in range(count)]