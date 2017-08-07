#include "X86InstrInfo.h"
#include "X86Subtarget.h"
#include "X86FaultInjection.h"
#include "X86MachineFunctionInfo.h"
#include "llvm/Target/TargetInstrInfo.h"
#include "llvm/CodeGen/MachineRegisterInfo.h"
#include "llvm/CodeGen/MachineBasicBlock.h"
#include "X86InstrBuilder.h"

using namespace llvm;

void X86FaultInjection::injectFault(MachineFunction &MF, std::vector<MCPhysReg> const &FIRegs,
        MachineBasicBlock &InstSelMBB, MachineBasicBlock &PreFIMBB,
        SmallVector<MachineBasicBlock *, 4> &OpSelMBBs, SmallVector<MachineBasicBlock *, 4> &FIMBBs,
        MachineBasicBlock &PostFIMBB) const
{
    const X86Subtarget &Subtarget = MF.getSubtarget<X86Subtarget>();
    const TargetInstrInfo &TII = *MF.getSubtarget().getInstrInfo();
    const MachineRegisterInfo &MRI = MF.getRegInfo();
    const TargetRegisterInfo &TRI = *MRI.getTargetRegisterInfo();
    X86MachineFunctionInfo *X86MFI = MF.getInfo<X86MachineFunctionInfo>();

    // XXX: PUSHF/POPF are broken: https://reviews.llvm.org/D6629
    assert(Subtarget.hasLAHFSAHF() && "Unsupported Subtarget: MUST have LAHF/SAHF\n");

    unsigned MaxRegSize = 0;
    // Find maximum size of target register to allocate stack space 
    for(auto FIReg : FIRegs) {
        const TargetRegisterClass *TRC = TRI.getMinimalPhysRegClass(FIReg);
        // Size is in bytes
        unsigned RegSize = TRC->getSize();
        MaxRegSize = RegSize > MaxRegSize ? RegSize : MaxRegSize;

        dbgs() << "FIReg:" << FIReg << ", RegName:" << TRI.getName(FIReg) << ", RegSizeBits:" << 8*RegSize<< ", ";
    }
    dbgs() << "\n";

    assert(MaxRegSize > 0 && "MaxRegSize must be > 0\n");

    /* ============================================================= CREATE InstSelMBB ========================================================== */

    // Stay clear of the red zone, 128 bytes
    // XXX: This MUST be done even FI in RSP, it will be adjusted anyway at PostFIMBB
    if(X86MFI->getUsesRedZone())
        // LEA to adjust RSP (does not clobber flags)
        addRegOffset(BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSP), X86::RSP, false, -128);

    unsigned RSPOffset = 0, RBPOffset = -8, RAXOffset = -16;
    // Save frame registers (RSP, RBP, RAX), use RBP for addressing
    {
        // PUSH RSP
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::RSP);
        // PUSH RBP
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::RBP);
        // RBP <- original RSP 
        addRegOffset(BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RBP), X86::RSP, false, -RBPOffset);

        // PUSH RAX used for saving flags, required by LAHF/SAHF instructions
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::RAX);
        // STORE flags
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::SETOr), X86::AL);
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::LAHF));
    }

    // XXX: Stack must be 16-byte aligned before calling a function. We don't know what's the alignment
    // before the call, so we do a double push scheme of RSP to align and restore it. Plus, PXOR for FI 
    // needs memory 16-byte aligned too. Align SP on a 16-byte boundary
    {
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::AND64ri8), X86::RSP).addReg(X86::RSP).addImm(-16);
    }

    {
        // PUSH R11 (preserve_all misses R11)
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::R11);
        // PUSH RDI for selInst arg1 (pointer stack, inject flag)
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::RDI);
        // Allocate stack space, XXX: 16-byte for alignment
        addRegOffset(BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSP), X86::RSP, false, -16);
        // MOV RDI <= RSP, selInst arg1
        addRegOffset(BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RDI), X86::RSP, false, 0);
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::CALL64pcrel32)).addExternalSymbol("selInst");
        // TEST for jump (see code later), XXX: THIS SETS FLAGS FOR THE JMP, be careful not to mess with them until the branch
        addDirectMem(BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::TEST8mi)), X86::RDI).addImm(0x1);

        addRegOffset(BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSP), X86::RSP, false, 16);
        // POP RDI
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(X86::RDI);
        // POP R11
        BuildMI(InstSelMBB, InstSelMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(X86::R11);

        SmallVector<MachineOperand, 1> Cond;
        Cond.push_back(MachineOperand::CreateImm(X86::COND_E));
        InstSelMBB.addSuccessor(&PostFIMBB);
        InstSelMBB.addSuccessor(&PreFIMBB);
        TII.InsertBranch(InstSelMBB, &PostFIMBB, &PreFIMBB, Cond, DebugLoc());
    }

    /* ============================================================= END OF InstSelMBB ========================================================== */

    /* ============================================================== CREATE PreFIMBB ============================================================== */

    // SystemV x64 calling conventions, args: RDI, RSI, RDX, RCX, R8, R9, XMM0-7, RTL
    // PUSH R11 (preserve_all misses R11)
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::R11);
    // PUSH RDI for doInject arg1 (unsigned, number of ops)
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::RDI);
    // PUSH RSI for doInject arg2 (uint64_t *, &op)
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::RSI);
    // PUSH RDX for doInject arg3 (uint64_t *, &size)
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::RDX);
    // PUSH RCX for doInject arg4 (uint64_t *, bitmask)
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(X86::RCX);
    // XXX: Align to 16B (5Regs * 8B !/ 16B), TODO: Create routine to auto-handle alignment
    addRegOffset(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSP), X86::RSP, false, -8);

    // The size and number of pointer arguments other than the bitmask
    unsigned PointerDataSize = 8;
    // SUB to create stack space for doInject arg2, arg3, arg4
    // TODO: Reduce stack space, ops, size array fit in uint16_t types
    unsigned AlignedStackSpace = (PointerDataSize + FIRegs.size() * PointerDataSize + MaxRegSize);
    // XXX: Align to 16-bytes
    AlignedStackSpace = AlignedStackSpace + ( (AlignedStackSpace%16) > 0 ? (16 - (AlignedStackSpace%16)) : 0 );
    addRegOffset(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSP), X86::RSP, false, -AlignedStackSpace);
    // MOV RDI <= FIRegs.size(), doInject arg1 (uint64_t, number of ops)
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::MOV64ri), X86::RDI).addImm(FIRegs.size());
    // LEA RSI <= &op, doInject arg2 (uint64_t *, &op, 8B)
    addRegOffset(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSI), X86::RSP, false, MaxRegSize + PointerDataSize * FIRegs.size());
    // LEA RDX <= &size, doInject arg3 (uint64_t *, &size, number of ops * 8B)
    addRegOffset(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RDX), X86::RSP, false, MaxRegSize);
    // MOV RDX <= RSP, doInject arg4 (uint8_t *, &bitmask, MaxRegSize B)
    addRegOffset(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RCX), X86::RSP, false, 0);
    // Fill in size array
    for(unsigned i = 0; i < FIRegs.size(); i++) {
        unsigned FIReg = FIRegs[i];
        const TargetRegisterClass *TRC = TRI.getMinimalPhysRegClass(FIReg);
        // Size is in bytes
        unsigned RegSize = TRC->getSize();
        MaxRegSize = RegSize > MaxRegSize ? RegSize : MaxRegSize;
        addRegOffset(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::MOV64mi32)), X86::RDX, false, i * PointerDataSize).addImm(RegSize);
    }

    //addDirectMem(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::MOV64mi32)), X86::RDI).addImm(0x0);
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::CALL64pcrel32)).addExternalSymbol("doInject");

    // POP doInject arg2, arg3, ar4
    addRegOffset(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSP), X86::RSP, false, AlignedStackSpace);
    // XXX: Alignment fix, FIXME
    addRegOffset(BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSP), X86::RSP, false, 8);
    // POP RCX
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(X86::RCX);
    // POP RDX
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(X86::RDX);
    // POP RSI
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(X86::RSI);
    // POP RDI
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(X86::RDI);
    // POP R11 (preserve_all misses R11)
    BuildMI(PreFIMBB, PreFIMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(X86::R11);

    PreFIMBB.addSuccessor(OpSelMBBs.front());
    TII.InsertBranch(PreFIMBB, OpSelMBBs.front(), nullptr, None, DebugLoc());

    /* ============================================================= END OF PreFIMBB ============================================================= */

    /* ============================================================== CREATE OpSelMBBs =============================================================== */

    unsigned OpSelStackOffset = 48 + AlignedStackSpace - MaxRegSize - PointerDataSize * FIRegs.size();
    // Jump tables to selected op
    for(int OpIdx = FIRegs.size()-1, OpSelIdx = 0; OpIdx > 0; OpIdx--, OpSelIdx++) { //no need to jump to 0th operand, fall through
        MachineBasicBlock &OpSelMBB = *OpSelMBBs[OpSelIdx];
        MachineBasicBlock *NextOpSelMBB = OpSelMBBs[OpSelIdx+1];
        addRegOffset(BuildMI(OpSelMBB, OpSelMBB.end(), DebugLoc(), TII.get(X86::CMP64mi8)), X86::RSP, false, -OpSelStackOffset).addImm(OpIdx);
        SmallVector<MachineOperand, 1> Cond;
        Cond.push_back(MachineOperand::CreateImm(X86::COND_E));
        OpSelMBB.addSuccessor(FIMBBs[OpIdx]);
        OpSelMBB.addSuccessor(NextOpSelMBB);
        TII.InsertBranch(OpSelMBB, FIMBBs[OpIdx], NextOpSelMBB, Cond, DebugLoc());
    }
    // Add the fall through OpSelMBB
    OpSelMBBs.back()->addSuccessor(FIMBBs[0]);
    TII.InsertBranch(*(OpSelMBBs.back()), FIMBBs[0], nullptr, None, DebugLoc());

    /* ============================================================== END OF OpSelMBBs =============================================================== */


    /* ============================================================== CREATE FIMBBs =============================================================== */
    // XXX: 48 = saved regs + args
    unsigned BitmaskStackOffset = 48 + AlignedStackSpace;
    for(unsigned idx = 0; idx < FIRegs.size(); idx++) {
        unsigned FIReg = FIRegs[idx];
        MachineBasicBlock &FIMBB = *FIMBBs[idx];

        const TargetRegisterClass *TRC = TRI.getMinimalPhysRegClass(FIReg);
        unsigned RegSize = TRC->getSize();
        unsigned RegSizeBits = RegSize * 8;

        // ProxyFIReg defaults to the register itself. It can be set to a different 
        // registers if FIReg = FLAGS | SP | RAX. FI operates on ProxyFIReg, and it 
        // is later copied to FIReg, if needed.
        unsigned ProxyFIReg = FIReg;

        // TODO: Test for 256-bit and 512-bit vector registers
        if(RegSizeBits <= 32) {
            // If it's one of the workhorse registers, used a different register as a proxy
            if(TRI.getSubRegIndex(X86::RSP, FIReg) || TRI.getSubRegIndex(X86::RBP, FIReg) || TRI.getSubRegIndex(X86::RAX, FIReg)) {
                ProxyFIReg = X86::RBX;

                unsigned RegStackOffset = 0;
                // Set the right offset in the stack
                if(TRI.getSubRegIndex(X86::RSP, FIReg))
                    RegStackOffset = RSPOffset;
                else if(TRI.getSubRegIndex(X86::RBP, FIReg))
                    RegStackOffset = RBPOffset;
                else if(TRI.getSubRegIndex(X86::RAX, FIReg))
                    RegStackOffset = RAXOffset;

                // PUSH Proxy to use for FI
                BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(ProxyFIReg);
                BitmaskStackOffset -= 8;
                addRegOffset(BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::MOV64rm), ProxyFIReg), X86::RBP, false, RegStackOffset);
            }
            // RAX is already the proxy for EFLAGS 
            else if(FIReg == X86::EFLAGS)
                ProxyFIReg = X86::RAX;

            addRegOffset(BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::XOR32rm), ProxyFIReg).addReg(ProxyFIReg), X86::RSP, false, -BitmaskStackOffset);

            if(TRI.getSubRegIndex(X86::RSP, FIReg) || TRI.getSubRegIndex(X86::RBP, FIReg) || TRI.getSubRegIndex(X86::RAX, FIReg)) {
                unsigned RegStackOffset = 0;
                // Set the right offset in the stack
                if(TRI.getSubRegIndex(X86::RSP, FIReg))
                    RegStackOffset = RSPOffset;
                else if(TRI.getSubRegIndex(X86::RBP, FIReg))
                    RegStackOffset = RBPOffset;
                else if(TRI.getSubRegIndex(X86::RAX, FIReg))
                    RegStackOffset = RAXOffset;

                // Store XOR result to stack
                addRegOffset(BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::MOV64mr)), X86::RBP, false, RegStackOffset).addReg(ProxyFIReg);
                // POP Proxy
                BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(ProxyFIReg);
            }
        }
        else if(RegSizeBits <= 64) {
            if(FIReg == X86::RSP || FIReg == X86::RBP || FIReg == X86::RAX) {
                ProxyFIReg = X86::RBX;

                unsigned RegStackOffset = 0;
                // Set the right offset in the stack
                if(FIReg == X86::RSP)
                    RegStackOffset = RSPOffset;
                else if(FIReg == X86::RBP)
                    RegStackOffset = RBPOffset;
                else if(FIReg == X86::RAX)
                    RegStackOffset = RAXOffset;

                // PUSH Proxy to use for FI
                BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::PUSH64r)).addReg(ProxyFIReg);
                BitmaskStackOffset -= 8;
                addRegOffset(BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::MOV64rm), ProxyFIReg), X86::RBP, false, RegStackOffset);
            }

            addRegOffset(BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::XOR64rm), ProxyFIReg).addReg(ProxyFIReg), X86::RSP, false, -BitmaskStackOffset);

            if(FIReg == X86::RSP || FIReg == X86::RBP || FIReg == X86::RAX) {
                unsigned RegStackOffset = 0;
                // Set the right offset in the stack
                if(FIReg == X86::RSP)
                    RegStackOffset = RSPOffset;
                else if(FIReg == X86::RBP)
                    RegStackOffset = RBPOffset;
                else if(FIReg == X86::RAX)
                    RegStackOffset = RAXOffset;

                // Store XOR result to stack
                addRegOffset(BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::MOV64mr)), X86::RBP, false, RegStackOffset).addReg(ProxyFIReg);
                // POP Proxy
                BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::POP64r)).addReg(ProxyFIReg);
            }
        }
        else if(RegSizeBits <= 128 || RegSizeBits <=256 || RegSizeBits <=512 ) {
            addRegOffset(BuildMI(FIMBB, FIMBB.end(), DebugLoc(), TII.get(X86::PXORrm), ProxyFIReg).addReg(ProxyFIReg), X86::RSP, false, -BitmaskStackOffset);
        }
        else 
            assert(false && "RegSizeBits is invalid!\n");

        FIMBB.addSuccessor(&PostFIMBB);
        TII.InsertBranch(FIMBB, &PostFIMBB, nullptr, None, DebugLoc());
    }

    /* ============================================================== END OF FIMBB =============================================================== */

    /* ============================================================ CREATE PostFIMBB ============================================================= */

    {
        // Restore EFLAGS
        BuildMI(PostFIMBB, PostFIMBB.end(), DebugLoc(), TII.get(X86::ADD8ri), X86::AL).addReg(X86::AL).addImm(INT8_MAX);
        BuildMI(PostFIMBB, PostFIMBB.end(), DebugLoc(), TII.get(X86::SAHF));
        addRegOffset(BuildMI(PostFIMBB, PostFIMBB.end(), DebugLoc(), TII.get(X86::MOV64rm), X86::RAX), X86::RBP, false, RAXOffset);
        addRegOffset(BuildMI(PostFIMBB, PostFIMBB.end(), DebugLoc(), TII.get(X86::MOV64rm), X86::RSP), X86::RBP, false, RSPOffset);
        // Restore RBP last 
        addRegOffset(BuildMI(PostFIMBB, PostFIMBB.end(), DebugLoc(), TII.get(X86::MOV64rm), X86::RBP), X86::RBP, false, RBPOffset);
    }

    if(X86MFI->getUsesRedZone())
        // LEA adjust SP
        addRegOffset(BuildMI(PostFIMBB, PostFIMBB.end(), DebugLoc(), TII.get(X86::LEA64r), X86::RSP), X86::RSP, false, 128);

    /* ============================================================ END OF PostFIMBB ============================================================= */
}

// code backup
#if 0
MachineInstr *MI = MO.getParent();
dbgs() << "another dump:"; MI->dump();
MachineBasicBlock::LivenessQueryResult LQR = MachineBasicBlock::LQR_Unknown;
MachineBasicBlock *MBB = MI->getParent();
MachineInstr &NextMI = *(++MI->getIterator());
dbgs() << "2. another dump:"; NextMI.dump();
LQR = MBB->computeRegisterLiveness(&TRI, X86::RAX, &NextMI);

dbgs() << "LQR: " << LQR << "\n";
//LQR = MachineBasicBlock::LQR_Live;
#endif

