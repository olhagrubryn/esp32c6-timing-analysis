#!/usr/bin/env python3
# scripts/base/registers.py

class RISCVRegisters:
    """Vollständige RISC-V Register für ESP32-C6."""
    
    # Temporary registers
    T0, T1, T2, T3, T4, T5, T6 = "t0", "t1", "t2", "t3", "t4", "t5", "t6"
    
    # Argument registers
    A0, A1, A2, A3, A4, A5, A6, A7 = "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7"
    
    # Saved registers
    S0, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11 = \
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11"
    
    # Register-Gruppen
    ALL_WORK_REGS = [T0,T1,T2,T3,T4,T5,T6,A0,A1,A2,A3,A4,A5,A6,A7,S0,S1,S2,S3,S4,S5,S6,S7,S8,S9,S10,S11]
    CHAIN_REGS = [T0,T1,T2,T3,T4,T5,T6,A0,A1,A2,A4,A5,A6,A7]
    BASE_REGS = [S0, S1, S2]
    INDEPENDENT_REGS = CHAIN_REGS
    
    @classmethod
    def get_all_work_registers(cls) -> list:
        return cls.ALL_WORK_REGS.copy()
    
    @classmethod
    def get_independent_registers(cls, count: int) -> list:
        regs = cls.INDEPENDENT_REGS
        return regs[:count] if count <= len(regs) else [regs[i % len(regs)] for i in range(count)]
    
    @classmethod
    def get_raw_chain_registers(cls, chain_length: int) -> list:
        all_regs = cls.T0,cls.T1,cls.T2,cls.T3,cls.T4,cls.T5,cls.T6,cls.A0,cls.A1,cls.A2,cls.A4,cls.A5,cls.A6,cls.A7,cls.S0,cls.S1,cls.S2,cls.S3,cls.S4,cls.S5,cls.S6,cls.S7,cls.S8,cls.S9,cls.S10,cls.S11
        return [all_regs[i % len(all_regs)] for i in range(chain_length)]
    
    @classmethod
    def get_register_combinations(cls) -> dict:
        return {
            "t_regs": [cls.T0, cls.T1, cls.T2],
            "a_regs": [cls.A0, cls.A1, cls.A2],
            "s_regs": [cls.S0, cls.S1, cls.S2],
            "mixed": [cls.T0, cls.A1, cls.S2],
            "same_reg": [cls.T0, cls.T0, cls.T0],
            "dst_src1": [cls.T0, cls.T0, cls.T1],
            "dst_src2": [cls.T0, cls.T1, cls.T0],
            "src1_src2": [cls.T1, cls.T1, cls.T1],
        }
    
    @classmethod
    def get_base_pointers(cls) -> list:
        return cls.BASE_REGS
    
    @classmethod
    def validate_register(cls, reg: str) -> bool:
        return reg in {'t0','t1','t2','t3','t4','t5','t6','a0','a1','a2','a3','a4','a5','a6','a7','s0','s1','s2','s3','s4','s5','s6','s7','s8','s9','s10','s11'}