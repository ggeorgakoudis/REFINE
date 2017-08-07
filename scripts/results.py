#!/usr/bin/env python3

import os
import sys
import subprocess
import timeit
import data
import re
from functools import partial
import multiprocessing as mp

try:
    appsdir = os.environ['APPSDIR']
except:
    print('Env variable APPSDIR is missing')
    sys.exit(1)

# main program
if len(sys.argv) < 4:
    print('Usage: results.py <tool name> <# start trial> <# end trial>')
    sys.exit(1)

tool = sys.argv[1]
istart = int(sys.argv[2])
iend = int(sys.argv[3])
print('appsdir %s tool %s istart %d iend %d'%(appsdir, tool, istart, iend))
appsdir = appsdir + tool + '/'

apps = [ 'AMG2013' , 'CoMD', 'HPCCG-1.0', 'lulesh', 'XSBench', 'miniFE', 'BT', 'CG', 'DC', 'EP', 'FT', 'LU', 'SP', 'UA' ]
for app in apps:
    print('app:'+app)
    os.chdir(appsdir + data.dirs[app]['appdir'])
    n_timeout = n_crash = n_soc = n_benign = 0
    verify_list = []
    with open('golden_output.txt', 'r') as f:
        s = f.read()
        for v in data.verify[app]:
            m = re.findall(v, s)
            verify_list += m

    for i in range(istart, iend+1):
        trialdir = appsdir + data.dirs[app]['appdir'] + tool + '/' + str(i) + '/'
        try:
            os.chdir(trialdir)
            ret_file = open('ret.txt', 'r')
        except FileNotFoundError:
            print('Missing exp: ' + tool + ' ' + app + ' ' + str(i))
            continue
        res = ret_file.read()
        res = res.strip().split(',')
        if res[0] == 'timeout':
            n_timeout += 1
        elif res[0] == 'crash':
            n_crash += 1
        elif res[0] == 'error':
            n_crash += 1
        elif res[0] == 'exit':
            with open('output.txt', 'r') as f:
                s = f.read()
                verified = True
                for out in verify_list:
                    if not out in s:
                        verified = False
                        break

                #print('verified:' + str(verified))
                if verified:
                    n_benign += 1
                else:
                    n_soc += 1
        else:
            print('Invalid result ' + tool + ' ' + app + ' ' + str(i) +' :' + str(res[0]))
        ret_file.close()

    os.chdir(appsdir + data.dirs[app]['appdir'])
    results_file = open('results-' + str(istart) + '-' + str(iend) + '.txt', 'w')
    results_file.write('timeout: ' + str(n_timeout) + '\n')
    results_file.write('crash: ' + str(n_crash) + '\n')
    results_file.write('soc: ' + str(n_soc) + '\n')
    results_file.write('benign: ' + str(n_benign) + '\n')
    results_file.close()
    print('\ttimeout: ' + str(n_timeout) + ', crash: ' + str(n_crash) + ', soc: ' + str(n_soc) + ', benign: ' + str(n_benign))

