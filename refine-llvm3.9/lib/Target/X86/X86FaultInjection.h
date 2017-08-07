#ifndef LLVM_LIB_TARGET_X86_X86FAULTINJECTION_H
#define LLVM_LIB_TARGET_X86_X86FAULTINJECTION_H

#include "llvm/Target/TargetFaultInjection.h"

namespace llvm {
    class X86FaultInjection : public TargetFaultInjection {
        public:
            X86FaultInjection() {}
            ~X86FaultInjection() override {}
            void injectFault(MachineFunction &MF, std::vector<MCPhysReg> const &FIRegs,
                    MachineBasicBlock &InstSelMBB, MachineBasicBlock &PreFIMBB,
                    SmallVector<MachineBasicBlock *, 4> &OpSelMBBs, SmallVector<MachineBasicBlock *, 4> &FIMBBs,
                    MachineBasicBlock &PostFIMBB) const override;
    };
} // end namespace llvm

#endif
