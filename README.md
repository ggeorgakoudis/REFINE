# REFINE: Realistic Fault Injection via Compiler-based Instrumentation

:zap: 
***REFINE has been superseeded by [SAFIRE](https://github.com/LLNL/SAFIRE), please redirect to https://github.com/LLNL/SAFIRE***

## Repo directory structure

injectlib: the fault injection library code implementing the single fault, random bit-flip fault model

pinfi: the tool implementing fault injection using Intel PIN

programs: contains the programs used for experimentation in four versions with respective subdirectories:

* golden: programs in vanilla version with no modification in their building process

* llfi: programs that their build process is modified to use the LLFI tool (https://github.com/DependableSystemsLab/LLFI) for fault injection

* pinfi: like golden, programs with no modifications for building using PINFI, the purpose of the subdirectory is store the output of experiments

* refine: programs that their building process is modified to use REFINE for fault injection

refine-llvm3.9: the REFINE LLVM compiler

results: .eps figures of the accuracy and performance results published in the SC'17 paper

scripts: the scripts for running experiments on LLNL CAB cluster and post-processing scripts for producing graphs and tables

## How to build and use the REFINE LLVM compiler

### Building the REFINE LLVM compiler
1. Clone the repo
2. Change directory to refine-llvm3.9

`cd refine-llvm3.9`

3. Download clang-3.9.0 (http://releases.llvm.org/3.9.0/cfe-3.9.0.src.tar.xz) and decompress it in the refine-llvm3.9/tools/ subdirectory
```
wget -P tools/ http://releases.llvm.org/3.9.0/cfe-3.9.0.src.tar.xz
tar -C tools/ -xf tools/cfe-3.9.0.src.tar.xz 
```

4. Create a directory for building, e.g., BUILD

`mkdir BUILD`

5. Change to the building directory

`cd BUILD`

6. Run cmake to boostrap the build proces and set the installation directory, e.g., 

`cmake -DCMAKE_INSTALL_PREFIX="$HOME/usr/local" -DLLVM_TARGETS_TO_BUILD="X86" -DCMAKE_BUILD_TYPE="Release" -DBUILD_SHARED_LIBS="ON" -DLLVM_OPTIMIZED_TABLEGEN="ON" ..`

7. Run the build program to process cmake generated build files, e.g.,

`make -j$(nproc)`

8. Install the REFINE LLVM compiler binaries, e.g.,

`make install`

### Using the REFINE LLVM compiler
1. Set the environment paths to include the installation directory, e.g.,

`export PATH="$HOME/usr/local/bin:$PATH"`

2. REFINE extends the LLVM compiler with fault injection flags. Those are:

|     Flag         |                 Description                       |
| -----------------| ------------------------------------------------- |
| -fi              | Enable REFINE fault injection in the LLVM backend       |
| -fi-funcs        | Comma separated list of functions to be possible FI targets. Setting to "*" selects all |
| -fi-inst-types   | Comma separated list of instruction types to be possible FI targets, possible values are: frame, control, data. Setting to "*" selects all |
| -fi-reg-types  | comma separated list of register types to be possible FI targets, possible types are: src, dst. Setting to "*" selects all

To include REFINE in the compilation process, you need to add the REFINE LLVM flags in the flags given to the compiler driver, such as `clang`. For example, using REFINE within a Makefile with CFLAGS variable is:

`CFLAGS += -mllvm -fi -mllvm -fi-funcs="*" -mllvm -fi-inst-types="*" -mllvm fi-reg-types="dst"`
REFINE flags enable fault injection to all functions, instructions and destination registers

This is the same example but invoking `clang` from the command line:

`clang -O3 -mllvm -fi -mllvm -fi-funcs="*" -mllvm -fi-inst-types="*" -mllvm fi-reg-types="dst"`

The `programs/refine` directory contains the programs and the modifications done in their build system, typically based on makefiles, for using REFINE

3. Besides compiling with REFINE flags, one needs to link an FI library that implements a specific fault model. We provide 
one which implements the single-fault, single bit-flip fault model in the `injectlib` directory. For the compilation process this means including the object file of the FI library in build process. For example, assuming the library we provide:
```
clang -O3 <REPO>/injectlib/doInject.c> -c -o doInject.o
clang -O3 -mllvm -fi -mllvm -fi-funcs="*" -mllvm -fi-inst-types="*" -mllvm fi-reg-types="dst" <...source files...> doInject.o
```

### Running an experiment with REFINE and the provided fault injection library

The FI library we provide needs a dynamic FI target instruction count to get the number of instructions for selecting a random instruction for FI. For that, it reads the number of dynamic target instructions from a file `refine-inscount.txt`. If the file is missing, the   library does the counting itself without injecting faults for this bootstrap run. 

In next runs, the library will read the dynamic target count from this file and perform fault injection. The FI library saves a log of fault injection in the file `refine-inject.txt` which contains the following entries: 
1. `fi_index`, the index of the dynamic nstruction the fault was injected to
2. `op`, the index of the operand the fault was injected to
3. `size`, the size in bytes of the operand
4. `biflip`, the position of the bit that was flipped

For example:
```
# Listing the initial working directory
$ ls
program
# First run of program
$ ./program <args>
<...FI library creates the refine-inscount.txt file...>
$ ls
program 
refine-inscount.txt
# Next run of program
$ ./program <args>
<...performs fault injection...>
$ ls 
program
refine-inscount.txt
refine-inject.txt
$ cat refine-inject.txt
fi_index=1869062110, op=1, size=4, bitflip=22
```

### Complete walkthrough example
TODO

## How to build and use the PINFI tool

### Building the PINFI tool

1. Download and install the Intel PIN framework (https://software.intel.com/en-us/articles/pin-a-binary-instrumentation-tool-downloads)
2. Copy the directory `pinfi` in the installed PIN path under `<PIN_PATH>/source/tools`
3. Change to the copied pinfi directory `cd <PIN_PATH>/source/tools/pinfi`
4. Run `make` to build the tool

Note, the PINFI tool is configurable to select whether to inject errors in source registers, destination registers or destination memory operands of instructions. This is possible by editing the file `utils.h` within the `pinfi` directory and including or excluding the preprocessor directives `FI_SRC_REG`, `FI_DST_REG`, `FI_DST_MEM` which control whether FI is enabled for their respective, self-descriptive targets. Also, The PINFI fault injection implementation follows too the single-fault, single bit-flip model.

### Using the PINFI tool

Similary to REFINE, PINFI must have a dynamic target instruction count before performing fault injection. This needs to bootstrap once for the same program and input. For this, PINFI includes an `instcount` tool to run before executing PINFI's `faultinjection` tool. 

For example:
```
$PIN_PATH/pin -t $PIN_PATH/source/tools/pinfi/obj-intel64/instcount -- ./program <args>
```
This will run the dynamic instruction counter and generate the `pin.instcount.txt` file that contains the number of dynamic target instructions. 

PINFI's fault injection tool reads this file to perform random fault injection. Running the fault injection tool:
```
$PIN_PATH/pin -t $PIN_PATH/source/tools/pinfi/obj-intel64/faultinjection -- ./program <args>
```

The PINFI tool produces a log of fault injection in the file `pin.injection.txt` which contains the following entries:
1. `fi_index`, the index of the dynamic nstruction the fault was injected to
2. `reg`, the symbolic register name the fault was injected to
3. `biflip`, the position of the bit that was flipped
4. `addr`, the instruction pointer address

### Citing REFINE
* Giorgis Georgakoudis, Ignacio Laguna, Dimitrios S. Nikolopoulos, and Martin Schulz. 2017. [REFINE: realistic fault injection via compiler-based instrumentation for accuracy, portability and speed.](https://dl.acm.org/citation.cfm?id=3126972) In Proceedings of the International Conference for High Performance Computing, Networking, Storage and Analysis (SC '17). ACM, New York, NY, USA, Article 29, 14 pages. DOI: https://doi.org/10.1145/3126908.3126972
