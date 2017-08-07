#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
import check_exps
import itertools

try:
    appsdir = os.environ['APPSDIR']
except:
    print('Env variable APPSDIR is missing')
    sys.exit(1)

parser = argparse.ArgumentParser('Run FI experiments')
parser.add_argument('-n', '--nodes', help='number of nodes', type=int, required=True)
parser.add_argument('-t', '--tools', help='tools list to experiment', nargs='+', required=True)
parser.add_argument('-p', '--partition', help='partition to run experiments', required=True)
parser.add_argument('-s', '--start', help='start trial', type=int, required=True)
parser.add_argument('-e', '--end', help='end trial', type=int, required=True)
args = parser.parse_args()

assert args.tools != None, 'Tools arg is missing'
assert args.nodes > 0, 'Nodes arg must be greater than 0'
assert args.partition in ['echo', 'local', 'debug', 'batch' ], 'Partition must be one of echo, local, debug, batch'
assert args.start != None, 'Start trial arg is missing'
assert args.end != None, 'End trial arg is missing'
assert args.start <= args.end, 'Start must be < end'

def chunkify(lst, n):
    return [ lst[i::n] for i in range(n)]

apps = [ 'AMG2013' , 'CoMD', 'HPCCG-1.0', 'lulesh', 'XSBench', 'miniFE', 'BT', 'CG', 'DC', 'EP', 'FT', 'LU', 'SP', 'UA' ]

exps = []
for t in args.tools:
    for app in apps:
        rem = check_exps.pending_exps(appsdir, t, app, args.start, args.end)
        if rem:
            exps+=[(t,app, x) for x in rem]

print('All exps: ' + str(len(exps)))

jobs = []
batch_lst = chunkify(exps, args.nodes)
for i, batch in enumerate(batch_lst):
    outf = open('srun-' + t + '-' + str(args.start) + '-' + str(args.end) + '-' + str(i) + '.out', 'w')
    errf = open('srun-' + t + '-' + str(args.start) + '-' + str(args.end) + '-' + str(i) + '.err', 'w')
    runargs = [['-e'] + [str(j) for j in e] for e in batch]
    runargs = [i for sub in runargs for i in sub]
    execlist=['./run.py'] + runargs
    #print(execlist)

    if args.partition  == 'echo':
        p = subprocess.Popen(['echo'] + execlist)
    elif args.partition in ['debug','batch']:
        if args.partition == 'debug':
            p = subprocess.Popen(['srun', '-N', '1', '-pp' + args.partition] + execlist)
        else:
            p = subprocess.Popen(['srun', '-N', '1', '-pp' + args.partition] + execlist, stdout = outf, stderr = errf)
    elif args.partition == 'local':
        p = subprocess.Popen(execlist)
    else:
        print('Invalid execution partition ' + args.partition)
    jobs.append({'tool':t, 'range': str(args.start) + '-' + str(args.end), 'proc': p})

try:
    for j in jobs:
        if j['proc'].wait() != 0:
            print('Error in process: ' + j['tool'] + ', range: ' + j['range'] +', ret: ' + str(j['proc'].returncode))
except KeyboardInterrupt:
    for j in jobs:
        j['proc'].terminate()
