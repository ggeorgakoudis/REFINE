#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <stdint.h>
#include <inttypes.h>
#include <assert.h>

void selInst(uint64_t *) __attribute__((preserve_all));
void doInject(unsigned , uint64_t *, uint64_t *, uint8_t *) __attribute__((preserve_all));
void init() __attribute__((constructor));
void fini() __attribute__((destructor));

/* initializes mt[NN] with a seed */
void init_genrand64(uint64_t seed);

/* generates a random number on [0, 2^64-1]-interval */
uint64_t genrand64_int64(void);

#define NN 312
#define MM 156
#define MATRIX_A UINT64_C(0xB5026F5AA96619E9)
#define UM UINT64_C(0xFFFFFFFF80000000) /* Most significant 33 bits */
#define LM UINT64_C(0x7FFFFFFF) /* Least significant 31 bits */

/* The array for the state vector */
static uint64_t mt[NN]; 
/* mti==NN+1 means mt[NN] is not initialized */
static int mti=NN+1; 

/* initializes mt[NN] with a seed */
void init_genrand64(uint64_t seed)
{
    mt[0] = seed;
    for (mti=1; mti<NN; mti++) 
        mt[mti] =  (UINT64_C(6364136223846793005) * (mt[mti-1] ^ (mt[mti-1] >> 62)) + mti);
}

/* generates a random number on [0, 2^64-1]-interval */
uint64_t genrand64_int64(void)
{
    int i;
    uint64_t x;
    static uint64_t mag01[2]={UINT64_C(0), MATRIX_A};

    if (mti >= NN) { /* generate NN words at one time */

        /* if init_genrand64() has not been called, */
        /* a default initial seed is used     */
        if (mti == NN+1) 
            init_genrand64(UINT64_C(5489)); 

        for (i=0;i<NN-MM;i++) {
            x = (mt[i]&UM)|(mt[i+1]&LM);
            mt[i] = mt[i+MM] ^ (x>>1) ^ mag01[(int)(x&UINT64_C(1))];
        }
        for (;i<NN-1;i++) {
            x = (mt[i]&UM)|(mt[i+1]&LM);
            mt[i] = mt[i+(MM-NN)] ^ (x>>1) ^ mag01[(int)(x&UINT64_C(1))];
        }
        x = (mt[NN-1]&UM)|(mt[0]&LM);
        mt[NN-1] = mt[MM-1] ^ (x>>1) ^ mag01[(int)(x&UINT64_C(1))];

        mti = 0;
    }
  
    x = mt[mti++];

    x ^= (x >> 29) & UINT64_C(0x5555555555555555);
    x ^= (x << 17) & UINT64_C(0x71D67FFFEDA60000);
    x ^= (x << 37) & UINT64_C(0xFFF7EEE000000000);
    x ^= (x >> 43);

    return x;
}

uint64_t dynFICount = 0;
uint64_t dynFIIndex = 0;
uint64_t dynFITarget = 0;
const char *inscount_fname = "refine-inscount.txt";
const char *out_fname = "refine-inject.txt";
FILE *ins_fp, *inj_fp;

void selInst(uint64_t *ret)
{
    *ret = 0;
    dynFIIndex++;

    if(dynFICount)
        if(dynFIIndex == dynFITarget)
            *ret = 1;
}

void doInject(unsigned num_ops, uint64_t *op, uint64_t *size, uint8_t *bitmask)
{
    *op = genrand64_int64()%num_ops;

    // XXX: size is in bytes, multiply by 8 for bits
    unsigned bitflip = (genrand64_int64()%(8*size[*op]));

    unsigned i;
    for(i=0; i<size[*op]; i++)
        bitmask[i] = 0;

    unsigned bit_i = bitflip/8;
    unsigned bit_j = bitflip%8;

    bitmask[bit_i] = (1U << bit_j);

    fprintf(inj_fp, "fi_index=%"PRIu64", op=%"PRIu64", size=%"PRIu64", bitflip=%u\n", dynFIIndex, *op, size[*op], bitflip);
    //printf("INJECTING FAULT: fi_index=%"PRIu64", op=%"PRIu64", size=%"PRIu64", bitflip=%u\n", dynFIIndex, *op, size[*op], bitflip);
    //fflush(stdout);
    fflush(inj_fp);
}

void init()
{
    uint64_t seed;
    FILE *fp = fopen("/dev/urandom", "r");
    assert(fp != NULL && "Error opening /dev/urandom\n");
    fread(&seed, sizeof(seed), 1, fp);
    init_genrand64(seed);
    assert(ferror(fp) == 0 && "Error reading /dev/urandom\n");
    fclose(fp);

    ins_fp = fopen(inscount_fname, "r");
    if(ins_fp) {
        fscanf(ins_fp, "%"PRIu64"\n", &dynFICount);
        assert(dynFICount > 0 && "dynFICount is invalid!\n");
        // Instruction count starts from 1
        dynFITarget = (genrand64_int64()%dynFICount) + 1;
        inj_fp = fopen(out_fname, "w");
        assert(inj_fp != NULL && "Error opening output file\n");
    }
}

void fini()
{
    if(dynFICount) {
        fclose(inj_fp);
        fclose(ins_fp);
    }
    else {
        fprintf(stderr, "PROFILING: dynamic count of FI instructions: %"PRIu64"\n", dynFIIndex);
        ins_fp = fopen(inscount_fname, "w");
        assert(ins_fp != NULL && "Error opening inscount file\n");
        fprintf(ins_fp, "%"PRIu64"\n", dynFIIndex);
        fclose(ins_fp);
    }
}

