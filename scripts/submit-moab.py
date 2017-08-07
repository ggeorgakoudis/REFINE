#!/usr/bin/env python3

import argparse
from datetime import date, time, datetime
import subprocess

def valid_walltime(s):
    try:
        return datetime.strptime(s, "%H:%M:%S").time()
    except ValueError:
        msg = "Not a valid time (HH:MM:SS): '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser('Submit FI experiments')
parser.add_argument('-n', '--nodes', help='number of nodes', type=int, required=True)
parser.add_argument('-w', '--walltime', help='wall time (HH:MM:SS)', type=valid_walltime, required=True)
parser.add_argument('-t', '--tools', help='tools list to experiment', nargs='+', required=True)
parser.add_argument('-s', '--start', help='start trial', type=int, required=True)
parser.add_argument('-e', '--end', help='end trial', type=int, required=True)
args = parser.parse_args()

assert args.nodes > 0, 'Nodes arg must be greater than 0'
assert args.tools != None, 'Tools arg is missing'
assert args.start != None, 'Start trial arg is missing'
assert args.end != None, 'End trial arg is missing'
assert args.start < args.end, 'Start must be < end'

fname = '.submit-moab-' + '-'.join(args.tools) + '-' + str(args.start) + '-' + str(args.end)  + '.sh'
with open(fname, 'w') as f:
    filestr = '#!/bin/bash\n'
    filestr += '#MSUB -l nodes=' + str(args.nodes) + '\n'
    filestr += '#MSUB -l partition=cab\n'
    filestr += '#MSUB -l walltime=' + str(args.walltime) + '\n'
    filestr += '#MSUB -q pbatch\n'
    filestr += '#MSUB -V\n'
    filestr += '#MSUB -o /usr/workspace/wsb/ggeorgak/job.out.%j.%N\n'
    filestr += 'date\n'
    filestr += 'pushd /g/g90/ggeorgak/projects/llnl/llvm-fi/scripts\n'
    filestr += 'export APPSDIR=$HOME/projects/llnl/bench-fi/\n'
    filestr += './experiments.py ' + '-n' + str(args.nodes) + ' -p batch' + ' -t ' + ' '.join(args.tools) + ' -s ' + str(args.start) + ' -e ' + str(args.end) + '\n'
    filestr += 'popd\n'
    filestr += 'date\n'

    f.write(filestr)

subprocess.run(['msub', fname])

