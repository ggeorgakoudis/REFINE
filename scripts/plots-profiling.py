#!/usr/bin/env python3

import os
import sys
import subprocess
import data
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats
import fi_tools
import argparse
import histogram

try:
    os.environ['APPSDIR']
except:
    print('Env variable APPSDIR is missing')
    sys.exit(1)

parser = argparse.ArgumentParser('This script create plots')
parser.add_argument('tools', help='tools list to experiment', nargs='+')
parser.add_argument('nsamples', help='number of timed profiling samples', nargs='+')
args = parser.parse_args()

def autolabel(width, ax, rects):
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., 1.00*height + err, '%.1f'%float(height), ha='center', va='bottom', fontsize=8)

apps = [ 'AMG2013' , 'CoMD', 'HPCCG-1.0', 'lulesh', 'BT', 'CG', 'DC', 'EP', 'FT', 'LU', 'SP', 'UA' ]
print(apps)
for app in apps:
    for tool in args.tools:
        appsdir = os.environ['APPSDIR'] + tool + '/' + data.dirs[app]['appdir']
        with open(appsdir + fi_tools.files['timeout'][tool]) as f:
            timeout = f.read()
            print('app: ' + app+ ', timeout: ' + timeout)

    continue #ggout
    # Create plots
    width = 0.5
    fig = plt.figure()
    err = 3 # %
    for idx, key in enumerate(plotdata.keys()):
        #ax = fig.add_subplot(2, len(plotdata.keys()), idx + 1)
        ax = fig.add_subplot(2, 3, idx+1)
        x = np.arange(len(args.tools))
        y = np.array(list(plotdata[key].values()))*100.0/n_samples
        yerr_neg = []
        for yy in y:
            if (yy-err) >= 0:
                yerr_neg.append(err)
            else:
                yerr_neg.append(yy)

        yerr_pos = [err for yy in y]
        rects = ax.bar(x, y, width = width, yerr=[yerr_neg, yerr_pos], capsize=2)
        ax.set_title(key)
        ax.set_ylabel('Results (%)')
        ax.set_xticks(x)
        labels = []
        for k in plotdata[key].keys():
            if k != 'refine-mbb':
                labels.append(k)
            else:
                labels.append('refine\n(mbb)')

        ax.set_xticklabels(plotdata[key].keys(), rotation='vertical', fontsize=10)
        [xmin, xmax] = ax.get_xlim()
        ax.set_xlim([xmin-2*width, xmax+2*width])
        [ymin, ymax] = ax.get_ylim()
        ax.set_ylim([ymin, ymax + 0.1*ymax])
        ax.tick_params(bottom='off')
        autolabel(width, ax, rects)

    idx = idx + 1
    n_samples = args.end-args.start+1
    ax = fig.add_subplot(2, 3, idx+1)
    x = np.arange(len(args.tools))
    ax.set_title('Summary')
    ax.set_ylabel('Results (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(args.tools, rotation='vertical', fontsize=10)
    results = ['crash+hang', 'soc', 'benign']
    bottom = [0 for xi in x]
    for i, r in enumerate(results):
        y = np.array(list(plotdata[r].values()))*100.0/n_samples
        ax.bar(x, y, width = width, bottom = bottom, label = r[0:3])
        bottom = y + bottom
        ax.legend(bbox_to_anchor = [.8, -.5], ncol=3, columnspacing=.5, fontsize=10, handlelength=1)

    #fig.suptitle(app)
    fig.tight_layout()
    #plt.show()
    plt.savefig(app+'.eps')

