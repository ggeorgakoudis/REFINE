#include<iostream>
#include<fstream>

#include <set>
#include <map>
#include <string>

#include <assert.h>

#include "pin.H"
#include "utils.h"
#include "instselector.h"

KNOB<string> instcount_file(KNOB_MODE_WRITEONCE, "pintool",
    "o", "pin.instcount.txt", "specify instruction count file name");

KNOB<string> fi_instr_file(KNOB_MODE_WRITEONCE, "pintool",
    "fi-instr", "pin.instrument.txt", "shows details of the instruction instrumentation");

static UINT64 fi_inst = 0;

std::fstream fi_instr_fstream;

VOID countInst() {
    fi_inst++;
}

// Pin calls this function every time a new instruction is encountered
VOID CountInst(INS ins, VOID *v)
{
  // XXX: Note is valid also performs injection type tests (SRC, DST, MEM_DST)
  if (!isValidInst(ins))
    return;

  fi_instr_fstream << "addr=" << hexstr(INS_Address(ins)) << ", instr=\"" << INS_Disassemble(ins) << "\"" << std::endl;

  INS_InsertPredicatedCall(
          ins, IPOINT_BEFORE, (AFUNPTR)countInst,
          IARG_END);	
}

VOID Fini(INT32 code, VOID *v)
{
    // Write to a file since cout and cerr maybe closed by the application
    ofstream OutFile;
    OutFile.open(instcount_file.Value().c_str());
    OutFile.setf(ios::showbase);
    OutFile << fi_inst << endl;
	    
	OutFile.close();
}

/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */

INT32 Usage()
{
    cerr << "This tool counts the number of dynamic instructions executed" << endl;
    cerr << endl << KNOB_BASE::StringKnobSummary() << endl;
    return -1;
}

int main(int argc, char * argv[])
{
    PIN_InitSymbols();
	// Initialize pin
    if (PIN_Init(argc, argv)) return Usage();

    configInstSelector();

    fi_instr_fstream.open(fi_instr_file.Value().c_str(), std::fstream::out);
    assert(fi_instr_fstream.is_open() && "Cannot open instrumentation output file\n");

    // Register Instruction to be called to instrument instructions
    INS_AddInstrumentFunction(CountInst, 0);

    // Register Fini to be called when the application exits
    PIN_AddFiniFunction(Fini, 0);
    
    // Start the program, never returns
    PIN_StartProgram();
    
    return 0;
}
