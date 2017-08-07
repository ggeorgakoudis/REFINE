#!/usr/bin/env python3

import os
import sys
import subprocess
import data
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats
import sklearn.metrics as metrics
import argparse
import histogram
import itertools

try:
    os.environ['APPSDIR']
except:
    print('Env variable APPSDIR is missing')
    sys.exit(1)

parser = argparse.ArgumentParser('This script creates the chi-square table')
parser.add_argument('tools', help='tools list to experiment', nargs='+')
parser.add_argument('start', help='start trial', type=int)
parser.add_argument('end', help='end trial', type=int)
parser.add_argument('tex', help='tex output')
args = parser.parse_args()

def autolabel(width, ax, rects):
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., 1.00*height + err, '%.1f'%float(height), ha='center', va='bottom', fontsize=8)

def gen_verdict(apps):
    verdict=[]
    for app in apps:
        try:
            #XXX: Remove soc category from CG, 0 for all tools
            if app == 'CG':
                cgtable = [results[app][tt][0:3:2] for tt in toolpair]
            else:
                cgtable = [results[app][tt] for tt in toolpair]
            chi2, pval, dof, expected = stats.chi2_contingency(cgtable)
            [print(toolpair[i]+' '+str(row)) for i,row in enumerate(cgtable)]
            pval = float('%.2f'%pval)
            print('app %s, t1 %s, t2 %s, pval %.6f:'%(app, toolpair[0], toolpair[1], pval)) # ggout
            if(pval < 1e-2):
                verdict.append('$\\approx%.2f$'%(pval))
            else:
                verdict.append('$%.2f$'%(pval))
            if pval < 0.05:
                verdict.append('\\textcolor{red}{yes}')
            else:
                verdict.append('\\textcolor{green}{no}')
        except:
            verdict.append('n/a')
    return verdict

apps = [ 'AMG2013' , 'CoMD', 'HPCCG-1.0', 'XSBench', 'miniFE', 'lulesh', 'BT', 'CG', 'DC', 'EP', 'FT', 'LU', 'SP', 'UA' ]
print(apps)
print(args.tools)
n_samples = args.end - args.start + 1
print('Generating results...')
#for tool in args.tools:
#    subprocess.run(['./results.py', tool, str(args.start), str(args.end)], stdout=subprocess.DEVNULL)

print('Running Chi-square test...')
results={}
for app in apps:
    results[app]={}
    for tool in args.tools:
        appsdir = os.environ['APPSDIR'] + tool + '/' + data.dirs[app]['appdir']
        results_fname = 'results-' + str(args.start) + '-' + str(args.end) + '.txt'
        cwd = os.getcwd()
        os.chdir(appsdir)

        output = app + ' ' + tool + ' '
        results_file = open(results_fname, 'r')
        n_timeout = int(results_file.readline().rstrip().split(':')[1]) #'timeout: ' + str(n_timeout) + '\n')
        n_crash = int(results_file.readline().rstrip().split(':')[1]) #'crash: ' + str(n_crash) + '\n')
        n_soc = int(results_file.readline().rstrip().split(':')[1]) #'soc: ' + str(n_soc) + '\n')
        n_benign = int(results_file.readline().rstrip().split(':')[1]) #'benign: ' + str(n_benign) + '\n')
        output += 'timeout: ' + str(n_timeout) + ' crash: ' + str(n_crash) + ' soc: ' + str(n_soc) + ' benign: ' + str(n_benign)
        results_file.close()
        #print(output)
        os.chdir(cwd)
        #results[tool] = { 'timeout' : n_timeout, 'crash' : n_crash, 'soc' : n_soc, 'benign' : n_benign }
        results[app][tool]= [(n_timeout+n_crash), n_soc, n_benign]
        #assert sum(results[app][tool]) == n_samples, 'Less number of samples, tool %s, app %s, samples %d, < %d'%(tool, app, sum(results[app][tool]), n_samples)
        if sum(results[app][tool]) < n_samples:
            print('Warning:less number of samples, tool %s, app %s, samples %d, < %d'%(tool, app, sum(results[app][tool]), n_samples))


print('Creating results table...')
print(results)
toolpairs=list(itertools.combinations(args.tools, 2))
toolpairs=[t for t in toolpairs if t[1] == 'pinfi']
with open(args.tex, 'w') as f:
    print('\\begin{tabular}{cc' + (len(apps[0:4])*2)*'c' + '}', file=f)
    print('\\toprule', file=f)
    #print('Base & Compassion & ' + ' & '.join(['\multicolumn{2}{c}{'+a+'}' for a in apps[0:4]]) + ' \\\\', file=f)
    print('Base & Compassion ' + 4*' & p-value & Signif. diff.?' + ' \\\\', file=f)
    for idx, toolpair in enumerate(toolpairs):
        print('\\midrule', file=f)
        print('& '.join(['\\textbf{'+t[0:7].upper()+'}' for t in toolpair]) + '&' + ' & '.join(['\multicolumn{2}{c}{'+a+'}' for a in apps[0:4]]) + ' \\\\', file=f)
        verdict=gen_verdict(apps[0:4])
        print('& &' + ' & '.join(verdict) + ' \\\\', file=f)
        print('\\midrule', file=f)
        print('& & ' + ' & '.join(['\multicolumn{2}{c}{'+a+'}' for a in apps[4:8]]) + ' \\\\', file=f)
        #print('& '+ len(apps[4:8])*' & p-value & Signif. diff.?' + ' \\\\ ', file=f)
        verdict=gen_verdict(apps[4:8])
        print('& &' + ' & '.join(verdict) + ' \\\\', file=f)
        print('\\midrule', file=f)
        print('& & ' + ' & '.join(['\multicolumn{2}{c}{'+a+'}' for a in apps[8:12]]) + ' \\\\', file=f)
        #print('& '+ len(apps[8:12])*' & p-value & Signif. diff.?' + ' \\\\ ', file=f)
        verdict=gen_verdict(apps[8:12])
        print('& &' + ' & '.join(verdict) + ' \\\\', file=f)
        print('\\midrule', file=f)
        print('& & ' + ' & '.join(['\multicolumn{2}{c}{'+a+'}' for a in apps[12:15]]) + ' \\\\', file=f)
        #print('& '+ len(apps[12:15])*' & p-value & Signif. diff.?' + ' \\\\ ', file=f)
        verdict=gen_verdict(apps[12:15])
        print('& &' + ' & '.join(verdict) + ' \\\\', file=f)

    print('\\bottomrule', file=f)
    print('\\end{tabular}', file=f)

