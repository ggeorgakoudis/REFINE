#!/usr/bin/env python3

import os
import sys
import subprocess
import timeit
import time
import re
from functools import partial
import multiprocessing as mp
import traceback
import numpy as np
import argparse

import build
import data
import fi_tools

def error_cb(error):
    traceback.format_exc()

try:
    appsdir = os.environ['APPSDIR']
except:
    print('Env variable APPSDIR is missing')
    sys.exit(1)

parser = argparse.ArgumentParser('Run a list of experiment tuples')
# tuple of 3: (tool, app, iter)
parser.add_argument('-e', '--exp', help='experiment to run', nargs=3, action='append', required=True)
args = parser.parse_args()

def run(exp):
    tool = exp[0]
    app = exp[1]
    trial = int(exp[2])
    t_timeout = exp[3]

    print('Fault injection ' + app + ' trial ' + str(trial) + ' started')
    trialdir = appsdir + '/' + tool + '/' + data.dirs[app]['appdir'] + '/' + tool + '/' + str(trial) + '/'
    if not os.path.exists(trialdir):
        os.makedirs(trialdir)

    os.chdir(trialdir)

    fi_tools.setup(tool, app, appsdir, trialdir)

    timed_out = False
    if not os.path.isfile('ret.txt'):
        out_file = open('output.txt', 'w')
        err_file = open('error.txt', 'w')
        ret = 0
        start = time.perf_counter()
        try:
            p = subprocess.run(fi_tools.get_fi_execlist(appsdir, tool, app), stdout=out_file, stderr=subprocess.DEVNULL, timeout = t_timeout)
            ret = p.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
        xtime = time.perf_counter() - start

        out_file.close()
        err_file.close()

        print('RET: ' + str(ret))
        ret_file = open('ret.txt', 'w')
        if timed_out:
            ret_file.write('timeout\n')
            print('Process timed out!')
        elif ret < 0:
            ret_file.write('crash, ' + str(ret) + '\n')
        elif ret > 0:
            ret_file.write('error, ' + str(ret) + '\n')
        else:
            ret_file.write('exit, ' + str(ret) + '\n')
        ret_file.close()

        print('time: %.2f'%(xtime))
        with open('time.txt', 'w') as f:
            f.write('%.2f'%(xtime) + '\n')

    fi_tools.cleanup(tool, app, appsdir, trialdir)

    print('Fault injection ' + app + ' trial ' + str(trial) + ' completed')

# Create pool of worker threads
n_workers = os.cpu_count()
pool = mp.Pool(n_workers)

exps = []
for e in args.exp:
    print(e)
    tool = e[0]
    app = e[1]
    trial = e[2]

    currdir = appsdir + '/' + tool + '/'

    os.chdir(currdir+data.dirs[app]['appdir'])

    profbin = fi_tools.get_profbin(appsdir, tool, app)
    fibin = fi_tools.get_fibin(appsdir, tool, app)
    # Build if exec is missing
    print('prof binary:' + profbin)
    print('fi binary:' + fibin)
    # XXX: if measuring compilation time is important, Clang should be in Release
    if not os.path.isfile(profbin) or not os.path.isfile(fibin):
    # force building
    #if True: # ggout
        print('Building and measuring time...')
        btime = timeit.repeat(lambda: build.build(currdir+data.dirs[app]['build']['dir'], data.dirs[app]['build']['args']), number=1, repeat=1)
        for idx, time in enumerate(btime):
            with open('compile-time-' + str(idx) + '.txt', 'w') as f:
                f.write('%.2f'%(time) + '\n')
        with open('mean-compile-time.txt', 'w') as f:
            f.write('%.2f'%(np.mean(btime)) + '\n')

    print('Executable is built')

    # Run once to get inscount if it's missing
    try:
        inscount_file = open(fi_tools.files['instcount'][tool], 'r')
        timeout_file = open('max-profiling-time.txt', 'r')
    except (FileNotFoundError, IOError):
        print('Profiling instruction count...')
        golden_out_file = open('golden_output.txt', 'w')
        t_timeout = timeit.repeat(lambda: subprocess.run(fi_tools.get_prof_execlist(appsdir, tool, app), stdout = golden_out_file), number = 1, repeat = 10)
        golden_out_file.close()
        for idx, time in enumerate(t_timeout):
            with open('profiling-time-' + str(idx) + '.txt', 'w') as f:
                f.write('%.2f'%(time) + '\n')
        with open('mean-profiling-time.txt', 'w') as f:
            f.write('%.2f'%(np.mean(t_timeout)) + '\n')
        with open('max-profiling-time.txt', 'w') as f:
            f.write('%.2f'%(max(t_timeout)) + '\n')

    with open('max-profiling-time.txt', 'r') as f:
        t_timeout = 3*float(f.readline())

    print('timeout (2x):' + '%.2f'%(t_timeout))
    print('Profiling instruction count done')
    exps.append(e+[t_timeout])

pool.map(run, exps, chunksize=int(max(1, len(exps)/n_workers)))

pool.close()
try:
    pool.join()
except KeyboardInterrupt:
    pool.terminate()
    pool.join()

