//===- MIRPrintingPass.cpp - Pass that prints out using the MIR format ----===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
// ggeorgak, 12/21/16 @ LLNL
//
//===----------------------------------------------------------------------===//
//
// This file implements a pass to do fault injection in machine code
//
//===----------------------------------------------------------------------===//

#include "llvm/CodeGen/Passes.h"
#include "llvm/CodeGen/MachineFunctionPass.h"

#include "llvm/Target/TargetInstrInfo.h"
#include "llvm/CodeGen/MachineRegisterInfo.h"

#include "llvm/Target/TargetSubtargetInfo.h"
#include "llvm/Target/TargetMachine.h"

#include <llvm/CodeGen/MachineInstrBuilder.h>
#include <llvm/Transforms/IPO/PassManagerBuilder.h>
#include <llvm/CodeGen/Passes.h>
#include "llvm/Pass.h"

#include "llvm/Analysis/Passes.h"
#include "llvm/CodeGen/AsmPrinter.h"
#include "llvm/CodeGen/BasicTTIImpl.h"
#include "llvm/CodeGen/MachineFunctionAnalysis.h"
#include "llvm/CodeGen/MachineModuleInfo.h"
#include "llvm/CodeGen/TargetPassConfig.h"
#include "llvm/IR/IRPrintingPasses.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Verifier.h"
#include "llvm/MC/MCAsmInfo.h"
#include "llvm/MC/MCContext.h"
#include "llvm/MC/MCInstrInfo.h"
#include "llvm/MC/MCStreamer.h"
#include "llvm/MC/MCSubtargetInfo.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/ErrorHandling.h"
#include "llvm/Support/FormattedStream.h"
#include "llvm/Support/TargetRegistry.h"
#include "llvm/Target/TargetLoweringObjectFile.h"
#include "llvm/Target/TargetOptions.h"
#include "llvm/Transforms/Scalar.h"
#include "llvm/MC/MCRegisterInfo.h"
#include "llvm/Support/RandomNumberGenerator.h"

using namespace llvm;

#define DEBUG_TYPE "mc-fi"

cl::opt<bool>
FIEnableOpt("fi", cl::desc("Enable fault injection at the instruction level"), cl::init(false));

cl::opt<bool>
FIMBBEnableOpt("fi-mbb", cl::desc("Enable fault injection at the MBB level"), cl::init(false));

cl::list<std::string>
FuncsOpt("fi-funcs", cl::CommaSeparated, cl::desc("Fault injected functions"), cl::value_desc("foo1, foo2, foo3, ..."));

cl::list<std::string>
FuncsExclOpt("fi-funcs-excl", cl::CommaSeparated, cl::desc("Exclude functions from fault injeciton"), cl::value_desc("foo1, foo2, foo3, ..."));

cl::list<std::string>
InstTypesOpt("fi-inst-types", cl::CommaSeparated, cl::desc("Fault injected instruction types"), cl::value_desc("data,control,frame"));

cl::list<std::string>
FIRegsOpt("fi-reg-types", cl::CommaSeparated, cl::desc("Fault injected registers"), cl::value_desc("dst, src"));

namespace {
  struct MCFaultInjectionPass : public MachineFunctionPass {
  private:
    enum InjectPoint {
      INJECT_BEFORE,
      INJECT_AFTER
    };

    int TotalInstrCount;
    int TotalSelInstrCount;
    int TotalFIInstrCount;
    bool FIEnable;
    bool FIMBBEnable;

    Module *M;
  public:
    static char ID;

    MCFaultInjectionPass() : MachineFunctionPass(ID) {
      FIEnable = FIEnableOpt;
      FIMBBEnable = FIMBBEnableOpt;

      TotalInstrCount = 0; TotalSelInstrCount = 0; TotalFIInstrCount = 0;
    }

    bool doInitialization(Module &M) override {
      this->M = &M;
      return false;
    }

    bool doFinalization(Module &M) override {
      //dbgs() << "MCFIPass finalize!" << "\n";
      return false;
    }

    void printMachineBasicBlock(MachineBasicBlock &MBB) {
      dbgs() << "MBB: " << MBB.getName() << ", " << MBB.getSymbol()->getName() << "\n";
      MBB.dump();
    }

    void printMachineFunction(MachineFunction &MF) {
      dbgs() << "MF: " << MF.getName() << "\n";
      for(auto &MBB : MF)
        printMachineBasicBlock(MBB);
    }

    void injectFault(MachineInstr &MI, std::vector<MCPhysReg> const &FIRegs, InjectPoint IT) {
      MachineBasicBlock &MBB = *MI.getParent();
      MachineFunction &MF = *MBB.getParent();
      MachineBasicBlock::instr_iterator Iter = MI.getIterator();
      const TargetFaultInjection *TFI = MF.getSubtarget().getTargetFaultInjection();
      const TargetInstrInfo &TII = *MF.getSubtarget().getInstrInfo();

      MachineBasicBlock *InstSelMBB = MF.CreateMachineBasicBlock(nullptr);
      MachineBasicBlock *PreFIMBB = MF.CreateMachineBasicBlock(nullptr);
      SmallVector<MachineBasicBlock *, 4> OpSelMBBs;
      SmallVector<MachineBasicBlock *, 4> FIMBBs;
      for(unsigned i = 0; i < FIRegs.size(); i++) {
        OpSelMBBs.push_back(MF.CreateMachineBasicBlock(nullptr));
        FIMBBs.push_back(MF.CreateMachineBasicBlock(nullptr));
      }
      MachineBasicBlock *PostFIMBB = MF.CreateMachineBasicBlock(nullptr);

      MachineFunction::iterator MBBI = MBB.getIterator();
      MF.insert(++MBBI, InstSelMBB);

      MBBI = InstSelMBB->getIterator();
      MF.insert(++MBBI, PreFIMBB);

      MBBI = PreFIMBB->getIterator();
      for(auto OpSelMBB : OpSelMBBs) {
        MF.insert(++MBBI, OpSelMBB);
        MBBI = OpSelMBB->getIterator();
      }

      MBBI = OpSelMBBs.back()->getIterator();
      for(auto FIMBB : FIMBBs) {
        MF.insert(++MBBI, FIMBB);
        MBBI = FIMBB->getIterator();
      }

      //MBBI = FIMBB->getIterator();
      MBBI = FIMBBs.back()->getIterator();
      MF.insert(++MBBI, PostFIMBB);

      //TFI->injectFault(MF, FIRegs, *PreFIMBB, *FIMBB, *PostFIMBB);
      TFI->injectFault(MF, FIRegs, *InstSelMBB, *PreFIMBB, OpSelMBBs, FIMBBs, *PostFIMBB);

      if(IT == INJECT_BEFORE)
        PostFIMBB->splice(PostFIMBB->end(), &MBB, Iter, MBB.end());
      else if(IT == INJECT_AFTER)
        PostFIMBB->splice(PostFIMBB->end(), &MBB, std::next(Iter), MBB.end());
      else
        assert(false && "InjectPoint is invalid!\n");

      PostFIMBB->transferSuccessors(&MBB);

      MachineBasicBlock *TBB = nullptr, *FBB = nullptr;
      SmallVector<MachineOperand, 4> Cond;
      // Add any additional MBB successors
      if(!TII.analyzeBranch(MBB, TBB, FBB, Cond)) {
        if(TBB) MBB.addSuccessor(TBB);
        if(FBB) MBB.addSuccessor(FBB);
      }

      MBB.addSuccessor(InstSelMBB);
      TII.InsertBranch(MBB, InstSelMBB, nullptr, None, DebugLoc());

      /*dbgs() << "============= MBB ============\n"; //ggout
      printMachineBasicBlock(MBB);
      dbgs() << "============= EOM ============\n";*/
      MBB.updateTerminator();
      InstSelMBB->updateTerminator();
      PreFIMBB->updateTerminator();
      for(auto OpSelMBB : OpSelMBBs)
        OpSelMBB->updateTerminator();
      for(auto FIMBB : FIMBBs)
        FIMBB->updateTerminator();
    }
    
    bool runOnMachineFunction(MachineFunction &MF) override {
      if(!FIEnable && !FIMBBEnable)
        return false;

      if(!FuncsOpt.empty())
        if(std::find(FuncsOpt.begin(), FuncsOpt.end(), "*") == FuncsOpt.end())
          if(std::find(FuncsOpt.begin(), FuncsOpt.end(), MF.getName()) == FuncsOpt.end()) {
            dbgs() << "Skip:" << MF.getName() << "\n";
            return false;
          }

      if(!FuncsExclOpt.empty()) {
        if(std::find(FuncsExclOpt.begin(), FuncsExclOpt.end(), "*") == FuncsExclOpt.end()) {
          if(std::find(FuncsExclOpt.begin(), FuncsExclOpt.end(), MF.getName()) != FuncsExclOpt.end()) {
            dbgs() << "Skip (EXCL):" << MF.getName() << "\n";
            return false;
          }
        }
        else {
          dbgs() << "Skip (EXCL):" << MF.getName() << "\n";
          return false;
        }
      }

      if(FIMBBEnable) {
        std::vector<MachineBasicBlock *> MBBs;
        /*dbgs() << "========== INJECTION ============\n";
        printMachineFunction(MF); //ggout
        dbgs() << "======= END OF INJECTION ========\n";*/

        for(auto &MBB : MF) {
          dbgs() << "MBB: " << MBB.getSymbol()->getName() << " ";
          unsigned count = 0;
          std::vector<MCPhysReg> FIRegs;
          dbgs() << "LiveIns: ";
          for(auto &Reg : MBB.liveins()) {
            const MachineRegisterInfo &MRI = MF.getRegInfo();
            const TargetRegisterInfo &TRI = *MRI.getTargetRegisterInfo();
            dbgs() << TRI.getName(Reg.PhysReg) << " ";
            FIRegs.push_back(Reg.PhysReg);
            count++;
          }

          // XXX: Some MBB have no instructionts, hence check with empty()
          if(count && !MBB.empty())
            MBBs.push_back(&MBB);

          dbgs() << "\n";
          continue;
        }

        for(auto MBB : MBBs) {
          unsigned count = 0;
          std::vector<MCPhysReg> FIRegs;
          dbgs() << "Inject: ";
          dbgs() << "MBB: " << MBB->getName() << ", " << MBB->getSymbol()->getName() << " ";
          for(auto &Reg : MBB->liveins()) {
            const MachineRegisterInfo &MRI = MF.getRegInfo();
            const TargetRegisterInfo &TRI = *MRI.getTargetRegisterInfo();
            dbgs() << TRI.getName(Reg.PhysReg) << " ";
            FIRegs.push_back(Reg.PhysReg);
            count++;
          }

          assert(count > 0 && "No liveins?");
          /*dbgs() << "===== BEGIN INST =====\n"; //ggout
          MBB->instr_begin()->dump();
          dbgs() << "===== END   INST =====\n";*/
          //injectFault(*MBB->instr_begin(), FIRegs[rand], INJECT_BEFORE);
          assert(FIRegs.size() > 0 && "FI Regs are 0!\n");
          injectFault(*MBB->instr_begin(), FIRegs, INJECT_BEFORE);
        }
      }
      else if(FIEnable) {
        std::vector<MachineInstr *> vecFIInstr;

        // TODO: Think whether error checking should be better, i.e., an invalid option at the
        // moment is ignored, perhaps reporting back an error is better
        bool doDataFI = false, doControlFI = false, doFrameFI = false;
        if(!InstTypesOpt.empty()) {
          if(std::find(InstTypesOpt.begin(), InstTypesOpt.end(), "data") != InstTypesOpt.end())
            doDataFI = true;

          if(std::find(InstTypesOpt.begin(), InstTypesOpt.end(), "control") != InstTypesOpt.end())
            doControlFI = true;

          if(std::find(InstTypesOpt.begin(), InstTypesOpt.end(), "frame") != InstTypesOpt.end())
            doFrameFI = true;

          assert((doDataFI || doControlFI || doFrameFI) && "FI instruction types is invalid!");
        }

        bool injectDstRegs = false, injectSrcRegs = false;
        if(!InstTypesOpt.empty()) {
          if(std::find(FIRegsOpt.begin(), FIRegsOpt.end(), "dst") != FIRegsOpt.end())
            injectDstRegs = true;

          if(std::find(FIRegsOpt.begin(), FIRegsOpt.end(), "src") != FIRegsOpt.end())
            injectSrcRegs = true;

          assert((injectDstRegs || injectSrcRegs) && "FI register types is invalid!");
        }

        dbgs() << "=============================================\n";
        dbgs() << "MF: " << MF.getName() << "\n";

        // Analyze instructions and put FI candidates in the vector vecFIInstr
        for(auto &MBB : MF) {
          //dbgs() << "MBB: " << MBB.getSymbol()->getName() << "\n";
          for(MachineBasicBlock::instr_iterator Iter = MBB.instr_begin(); Iter != MBB.instr_end(); Iter++) {
            bool isData = false, isControl = false, isFrame = false;
            MachineInstr &MI = *Iter;

            if(!MI.isPseudo()) { 
              TotalInstrCount++;
              //MI.dump();

              if(MI.isBranch() || MI.isCall() || MI.isReturn())
                isControl = true;
              else if(MI.getFlag(MachineInstr::FrameSetup) || MI.getFlag(MachineInstr::FrameDestroy))
                isFrame = true;
              else
                isData = true;

              //dbgs() << (isData?"data, ":"") << (isControl?"control," :"") << (isFrame?"frame,":"") << " ";
              //dbgs() << "isMem:" << (MI.mayLoadOrStore()?"true":"false") << ", ";

              // Skip instructions based on FI inst types
              if(!doFrameFI && isFrame) {
                dbgs() << "skip frame instr\n";
                continue;
              }

              if(!doDataFI && isData) {
                dbgs() << "skip data instr\n";
                continue;
              }

              if(!doControlFI && isControl) {
                dbgs() << "skip control instr\n";
                continue;
              }

              assert((isData || isFrame || isControl) && "Instruction type is invalid!\n");

              bool isSelInstr = false;
              // Find if the instruction is eligible based on the operand selection
              for(auto MOIter = MI.operands_begin(); MOIter != MI.operands_end(); MOIter++) {
                MachineOperand &MO = *MOIter;

                if(MO.isReg() && MO.getReg()) {
                  if(injectSrcRegs && MO.isUse())
                    isSelInstr = true;
                  else if(injectDstRegs && MO.isDef())
                    isSelInstr = true;
                }

                if(isSelInstr)
                  break;
              }

              if(isSelInstr) {
                vecFIInstr.push_back(&MI);
                TotalSelInstrCount++;
              }
            }
          }
        }

        for(auto MI : vecFIInstr) {
          std::vector<MachineOperand *> EligibleOps;

          dbgs() << "MBB: " << MI->getParent()->getSymbol()->getName() << ", ";
          dbgs() << "FI-MI: ";
          MI->dump();
          for(auto MOIter = MI->operands_begin(); MOIter != MI->operands_end(); MOIter++) {
            MachineOperand &MO = *MOIter;
            //dbgs() << "MO:"; dbgs() << MO << ", ";
            //if(MO.isReg())
            //  dbgs() << "isReg: " << MO.isReg() << ", getReg: " << MO.getReg() << ", isUse: " << MO.isUse() << ", isDef: " << MO.isDef() << "\n";

            if(MO.isReg() && MO.getReg()) {
              if(injectSrcRegs && MO.isUse())
                EligibleOps.push_back(&MO);
              else if(injectDstRegs && MO.isDef())
                EligibleOps.push_back(&MO);
            }
          }

          if(EligibleOps.empty())
            dbgs() << "No suitable operands to inject error\n";
          else {
            const MachineRegisterInfo &MRI = MF.getRegInfo();
            const TargetRegisterInfo &TRI = *MRI.getTargetRegisterInfo();

            // XXX: Inject errors only on super-registers to avoid duplicates
            EligibleOps.erase(std::remove_if(EligibleOps.begin(), EligibleOps.end(),
                [&TRI, &MRI, EligibleOps](MachineOperand *a) {
                for(auto b : EligibleOps)
                  if(TRI.getSubRegIndex(b->getReg(), a->getReg())) return true;
                return false;
                }), EligibleOps.end());
            dbgs() << "EligibleOps: " << EligibleOps.size() << ", ";
            // XXX: WARNING! CAUTION! This implementation assumes FI happens *ONLY* in DST registers, 
            // thus it's always inserted after the instruction to instrument
            // TODO: SRC Registers
            //MachineOperand *MO = EligibleOps[rnd_idx];
            //injectFault(*MI, MO->getReg(), (MO->isUse()?INJECT_BEFORE:INJECT_AFTER));
            // XXX: Convert from MO vector to MCPhysReg vector. I'm keeping old code for continuity and 
            // upgradeability
            std::vector<MCPhysReg> FIRegs;
            for(auto MO : EligibleOps)
              if(MO->isDef()) {
                dbgs() << TRI.getName(MO->getReg()) << ", ";
                FIRegs.push_back(MO->getReg());
              }

            // XXX: AGAIN, only INJECT_AFTER
            injectFault(*MI, FIRegs, INJECT_AFTER);
            TotalFIInstrCount++;
          }
        }

        dbgs() << "=============================================\n";
        dbgs() << "TotalInstrCount: " << TotalInstrCount << ", TotalSelInstrCount:" << TotalSelInstrCount 
          << ", TotalFIInstrCount: " << TotalFIInstrCount << "\n";
        dbgs() << "=============================================\n";

      }

      return true;
    }
  };

} // end anonymous namespace

char MCFaultInjectionPass::ID = 0;
char &llvm::MCFaultInjectionPassID = MCFaultInjectionPass::ID;

INITIALIZE_PASS(MCFaultInjectionPass, "mc-fi", "MC FI Pass", false, false)

namespace llvm {

  MachineFunctionPass *createMCFaultInjectionPass() {
    return new MCFaultInjectionPass();
  }

}

