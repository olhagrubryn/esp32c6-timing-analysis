#!/usr/bin/env python3
# scripts/base/registers.py - Vollständige RISC-V Register-Definitionen

class RISCVRegisters:
    """
    Definiert alle verfügbaren RISC-V Register für ESP32-C6.
    Alle general-purpose Register sind architektonisch identisch.
    Die ABI-Namen sind nur Konventionen und beeinflussen nicht die Performance.
    """
    
    # =======================================================
    # ALLE general-purpose Register (x1-x31)
    # =======================================================
    
    # Temporary registers (t0-t6) - für allgemeine Berechnungen
    T0 = "t0"   # x5
    T1 = "t1"   # x6
    T2 = "t2"   # x7
    T3 = "t3"   # x28
    T4 = "t4"   # x29
    T5 = "t5"   # x30
    T6 = "t6"   # x31
    
    # Argument registers (a0-a7) - für Funktionsargumente
    A0 = "a0"   # x10
    A1 = "a1"   # x11
    A2 = "a2"   # x12
    A3 = "a3"   # x13
    A4 = "a4"   # x14
    A5 = "a5"   # x15
    A6 = "a6"   # x16
    A7 = "a7"   # x17
    
    # Saved registers (s0-s11) - für langfristige Speicherung
    S0 = "s0"   # x8
    S1 = "s1"   # x9
    S2 = "s2"   # x18
    S3 = "s3"   # x19
    S4 = "s4"   # x20
    S5 = "s5"   # x21
    S6 = "s6"   # x22
    S7 = "s7"   # x23
    S8 = "s8"   # x24
    S9 = "s9"   # x25
    S10 = "s10" # x26
    S11 = "s11" # x27
    
    # =======================================================
    # Register-Gruppen für verschiedene Zwecke
    # =======================================================
    
    # ALLE verfügbaren Arbeitsregister (ohne x0, ra, sp, gp, tp)
    ALL_WORK_REGS = [
        # Temporary registers (7 Stück)
        T0, T1, T2, T3, T4, T5, T6,
        # Argument registers (8 Stück)
        A0, A1, A2, A3, A4, A5, A6, A7,
        # Saved registers (12 Stück - für lange Chains)
        S0, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11
    ]  # Insgesamt 27 Register!
    
    # Für Dependency Chains - temporäre und Argument-Register
    CHAIN_REGS = [
        T0, T1, T2, T3, T4, T5, T6,
        A0, A1, A2, A4, A5, A6, A7  # A3 ist für Base-Pointer reserviert
    ]
    
    # Für Load/Store - Basis-Register (Saved registers für Stabilität)
    BASE_REGS = [S0, S1, S2]  # s0, s1, s2 als Base-Pointer
    
    # Für RAW Chains - alle verfügbaren Register
    DST_REGS = CHAIN_REGS  # Destination Register
    SRC_REGS = CHAIN_REGS  # Source Register
    
    # Für Throughput - unabhängige Register
    INDEPENDENT_REGS = CHAIN_REGS
    
    @classmethod
    def get_all_work_registers(cls) -> list:
        """Alle verfügbaren Arbeitsregister (27 Stück)."""
        return cls.ALL_WORK_REGS.copy()
    
    @classmethod
    def get_independent_registers(cls, count: int) -> list:
        """
        Generiert unabhängige Register für Throughput-Messungen.
        Stellt sicher, dass genügend verschiedene Register verfügbar sind.
        """
        if count <= len(cls.INDEPENDENT_REGS):
            return cls.INDEPENDENT_REGS[:count]
        # Bei Bedarf zyklisch wiederholen
        return [cls.INDEPENDENT_REGS[i % len(cls.INDEPENDENT_REGS)] 
                for i in range(count)]
    
    @classmethod
    def get_raw_chain_registers(cls, chain_length: int) -> list:
        """
        Generiert Register für eine RAW Dependency Chain.
        Für lange Ketten werden Saved-Register verwendet.
        """
        # Für Ketten > 14 verwende auch Saved-Register
        if chain_length <= len(cls.CHAIN_REGS):
            return cls.CHAIN_REGS[:chain_length]
        
        # Für sehr lange Ketten: zyklisch mit allen verfügbaren Registern
        all_regs = cls.T0, cls.T1, cls.T2, cls.T3, cls.T4, cls.T5, cls.T6, \
                   cls.A0, cls.A1, cls.A2, cls.A4, cls.A5, cls.A6, cls.A7, \
                   cls.S0, cls.S1, cls.S2, cls.S3, cls.S4, cls.S5, cls.S6, \
                   cls.S7, cls.S8, cls.S9, cls.S10, cls.S11
        
        return [all_regs[i % len(all_regs)] for i in range(chain_length)]
    
    @classmethod
    def get_register_combinations(cls) -> dict:
        """
        Verschiedene Register-Kombinationen für Tests.
        Testet, ob Ergebnisse unabhängig von der Registerwahl sind.
        """
        return {
            "t_regs": [cls.T0, cls.T1, cls.T2],        # Nur temporäre
            "a_regs": [cls.A0, cls.A1, cls.A2],        # Nur Argument
            "s_regs": [cls.S0, cls.S1, cls.S2],        # Nur Saved
            "mixed": [cls.T0, cls.A1, cls.S2],         # Gemischt
            "same_reg": [cls.T0, cls.T0, cls.T0],      # Gleiches Register
            "dst_src1": [cls.T0, cls.T0, cls.T1],      # dst = src1
            "dst_src2": [cls.T0, cls.T1, cls.T0],      # dst = src2
            "src1_src2": [cls.T1, cls.T1, cls.T1],     # src1 = src2
        }
    
    @classmethod
    def get_base_pointers(cls) -> list:
        """
        Basis-Pointer für Load/Store Operationen.
        Verwendet Saved-Register für Stabilität.
        """
        return cls.BASE_REGS
    
    @classmethod
    def validate_register(cls, reg: str) -> bool:
        """Prüft, ob ein Register gültig ist."""
        valid_regs = {
            't0', 't1', 't2', 't3', 't4', 't5', 't6',
            'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7',
            's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 's10', 's11'
        }
        return reg in valid_regs