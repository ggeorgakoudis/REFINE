#ifndef FAULT_INJECTION_H
#define FAULT_INJECTION_H

#include <map>
#include "pin.H"
#include "stdio.h"
#include "stdlib.h"
#include <iostream>
#include <fstream>
#include <time.h>


// TODO: Fix the knob to select the FI instruction types
//KNOB<string> fioption(KNOB_MODE_WRITEONCE, "pintool", "fioption", "", "specify fault injection option: all, sp, fp, ccs");

// XXX: MAX_OPS should be always greater than the maximum nuber of implicit and explicit operands
#define MAX_OPS 32


using namespace std;

std::fstream fi_output_fstream;
//std::fstream fi_instr_fstream;

#endif
