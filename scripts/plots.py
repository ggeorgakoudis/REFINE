#!/usr/bin/env python3

import os
import sys
import subprocess
import data
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import scipy.stats as stats
import sklearn.metrics as metrics
import argparse
import histogram

try:
    os.environ['APPSDIR']
except:
    print('Env variable APPSDIR is missing')
    sys.exit(1)

parser = argparse.ArgumentParser('This script create plots')
parser.add_argument('tools', help='tools list to experiment', nargs='+')
parser.add_argument('start', help='start trial', type=int)
parser.add_argument('end', help='end trial', type=int)
args = parser.parse_args()

# These are the "Tableau 20" colors as RGB.
tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),
	(44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),
	(148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),
	(227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),
	(188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]

# Tableau Color Blind 10
tableau20blind = [(0, 107, 164), (255, 128, 14), (171, 171, 171), (89, 89, 89),
        (95, 158, 209), (200, 82, 0), (137, 137, 137), (163, 200, 236),
        (255, 188, 121), (207, 207, 207)]
# Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.
for i in range(len(tableau20)):
    r, g, b = tableau20[i]
    tableau20[i] = (r / 255., g / 255., b / 255.)
for i in range(len(tableau20blind)):
    r, g, b = tableau20blind[i]
    tableau20blind[i] = (r / 255., g / 255., b / 255.)

def autolabel(width, ax, rects, err):
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., 1.00*height + err, '%.1f'%float(height), ha='center', va='bottom', fontsize=matplotlib.rcParams['font.size']-4, rotation=0)
        #ax.text(rect.get_x() + rect.get_width()/2., 1.00*height + err, '%.1f'%float(height), ha='center', va='bottom', fontsize=matplotlib.rcParams['font.size']-4, rotation=0)

apps = [ 'AMG2013' , 'CoMD', 'HPCCG-1.0', 'XSBench', 'miniFE', 'lulesh', 'BT', 'CG', 'DC', 'EP', 'FT', 'LU', 'SP', 'UA' ]
print(apps)
print('Generating results...')
#for tool in args.tools:
#        subprocess.run(['./results.py', tool, str(args.start), str(args.end)], stdout=subprocess.DEVNULL)

total_timings={}
for t in args.tools:
    total_timings[t] = 0

n_samples = args.end-args.start+1

print('Creating plots...')
for app in apps:
    print('app:'+app)
    #results = { 'timeout':{}, 'crash': {}, 'crash+hang': {}, 'soc': {}, 'benign':{} }
    results = { 'crash': {}, 'soc': {}, 'benign':{} }
    timings = {}
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
        print(output)
        os.chdir(cwd)
        #results[tool] = { 'timeout' : n_timeout, 'crash' : n_crash, 'soc' : n_soc, 'benign' : n_benign }
        results['crash'][tool] = n_crash + n_timeout
        results['soc'][tool] = n_soc
        results['benign'][tool] = n_benign
        n_total = sum(results[k][tool] for k in results.keys())
        assert n_total == n_samples, 'Less num samples: ' + str(n_total) + '< ' + n_samples

        timing=0
        for idx in range(args.start, args.end+1):
            trialdir = appsdir + tool + '/' + str(idx) + '/'
            try:
                with open(trialdir+'time.txt', 'r') as f:
                        timing += float(f.readline())
            except FileNotFoundError as e:
                print(e)
                timing += 0
        timings[tool]=timing
        total_timings[tool]+=timing

    print(results)
    print(timings)

    # Compute distance
    '''ref=np.array([results[k]['pinfi']/n_samples for k in ('crash+hang', 'soc', 'benign')])
    print('ref:' + str(ref))
    nrows = 1
    ncols = 4
    idx = 0
    fig = plt.figure()
    for tool in args.tools:
        dat=np.array([results[k][tool]/n_samples for k in ('crash+hang', 'soc', 'benign')])
        #print('data:' + str(dat))
        # euclidean
        eu_dist=np.linalg.norm(dat-ref)
        #print('Euclid dist ref: pinfi, tool: '+tool+' = %.2lf'%(eu_dist))
        # Pearson coeff
        pr = stats.pearsonr(ref, dat)
        print('Pearson coef ref: pinfi, tool: '+tool+' =  '+str(pr))
        # Kullback-Leibler divergence
        kl = stats.entropy(dat, ref, 2)
        #print('Kullback-Leibler diverg. ref: pinfi, tool: '+tool+' = '+str(kl))
        # Mutual info metric
        mi = metrics.mutual_info_score(ref, dat)
        #print('Mutual info metric ref: pinfi, tool: '+tool+' = '+str(mi))
        # Hellinger distance
        hd = np.linalg.norm(np.sqrt(dat) - np.sqrt(ref)) / np.sqrt(2)
        print('Hellinger distance ref: pinfi, tool: '+tool+' = %.2f'%(hd))
        # Bhattacharya distance
        bd = histogram.fidelity_based(dat, ref)
        print('Fidelity distance ref: pinfi, tool: '+tool+' = %.2f'%(bd))
        # Histogram intersection
        hi = histogram.histogram_intersection(dat, ref)
        print('Histogram intersection ref: pinfi, tool: '+tool+' = %.2f'%(hi))
        keys = [ 'crash+hang', 'soc', 'benign' ]
        print('data:'+str([results[k][tool] for k in keys]))
        hist_data = [results[k][tool]*100./n_samples for k in keys]
        fig.add_subplot(nrows, ncols, idx+1)
        plt.ylim(0, 100)
        plt.title(tool)
        plt.bar(range(0, len(hist_data)), hist_data)
        idx+=1
    print('================')
    #plt.show()

    #continue # ggout'''

    # Create plots
    matplotlib.rcParams.update({'font.size': 14})
    width = 0.66
    fig = plt.figure()
    err = 3 # %
    nrows = 4
    ncols = 4
    keys = [ 'crash', 'soc', 'benign' ]
    rects_all=[]
    for idx, key in enumerate(keys):
        ax = fig.add_subplot(nrows, ncols, idx+1)
        x = np.arange(0, 2*len(args.tools), 2)
        y = np.array([results[key][t]*100.0/n_samples for t in args.tools])#list(results[key].values()))*100.0/n_samples
        yerr_neg = []
        for yy in y:
            if (yy-err) >= 0:
                yerr_neg.append(err)
            else:
                yerr_neg.append(yy)

        yerr_pos = [err for yy in y]
        rects = ax.bar(x, y, width = width, yerr=[yerr_neg, yerr_pos], capsize=2, color=tableau20blind[idx])
        rects_all = rects_all + [(ax, r) for r in rects]
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_title(key)
        #ax.set_ylim([0,100])
        if (idx == 0):
            ax.set_ylabel('Results (%)')
        #ax.plot(x, [results[key]['pinfi']*100.0/n_samples for xi in x], color='black', linestyle='--')
        ax.set_xticks(x)
        labels = []
        for k in results[key].keys():
            if k != 'refine-mbb':
                labels.append(k)
            else:
                labels.append('refine\n(mbb)')

        ax.set_xticklabels([t[0:7].upper() for t in args.tools], rotation='vertical', fontsize=matplotlib.rcParams['font.size']-2)
        [xmin, xmax] = ax.get_xlim()
        ax.set_xlim([xmin-2*width, xmax+2*width])
        [ymin, ymax] = ax.get_ylim()
        ax.set_ylim([ymin, ymax + 0.1*ymax])
        ax.tick_params(bottom='off')
        #autolabel(width, ax, rects, err)
    for i, t in enumerate(args.tools):
        tool_rects = rects_all[i::3]
        for ax, rect in tool_rects:
            height = rect.get_height()
            val = '%.1f'%float(height)
            # if last tool do the subtraction from 100%
            if rect == tool_rects[-1][1]:
                val = '%.1f'%(100 - sum([float('%.1f'%r.get_height()) for ax, r in tool_rects[:-1]]))
            ax.text(rect.get_x() + rect.get_width()/2., 1.00*height + err, val, ha='center', va='bottom', fontsize=matplotlib.rcParams['font.size']-4)


    width = 0.5
    idx = idx + 1
    n_samples = args.end-args.start+1
    ax = fig.add_subplot(nrows, ncols, idx+1)
    x = np.arange(0, len(args.tools))
    #ax.set_title('Summary')
    #ax.set_ylabel('Results (%)')
    ax.set_xticks(x)
    ax.set_xticklabels([t[0:7].upper() for t in args.tools], rotation='vertical', fontsize=matplotlib.rcParams['font.size']-2)
    categories = ['crash', 'soc', 'benign']
    bottom = [0 for xi in x]
    for i, r in enumerate(categories):
        y = np.array([results[r][t]*100.0/n_samples for t in args.tools])
        ax.bar(x, y, width = width, bottom = bottom, label = r[0:3], color=tableau20blind[i])
        bottom = y + bottom
        #ax.legend(bbox_to_anchor = [1.45, 1.35], ncol=3, columnspacing=.35, handlelength=1, frameon=False)
        ax.legend(loc=[-.25, 1.0], ncol=3, columnspacing=.35, handlelength=1, frameon=False, fontsize=matplotlib.rcParams['font.size']-2)

    fig.tight_layout(pad=-1.0, w_pad=-0.75, h_pad=-1.0)
    #fig.tight_layout()
    #plt.show()
    plt.savefig(app+'.eps', bbox_inches='tight')
    plt.close()

    # Un-normed time plots
    matplotlib.rcParams.update({'font.size': 24})
    fig, ax = plt.subplots()
    y = np.array([timings[t]/3600.0 for t in args.tools])
    ax.set(xticks=x, ylabel='Time (h)')#, title=app)
    ax.set_xticklabels([t[0:7].upper() for t in args.tools], rotation='vertical')
    rects = plt.bar(x, y, color=tableau20blind[0])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    autolabel(width, ax, rects, 0)
    plt.savefig(app+'-time.eps', bbox_inches='tight')
    plt.close()

    # Normed (PINFI) time plots
    matplotlib.rcParams.update({'font.size': 32})
    fig, ax = plt.subplots()
    # copy list
    tools = args.tools[:]
    # remove pinfi used for norm
    tools.remove('pinfi')
    x = range(0, len(tools))
    y = np.array([timings[t]/timings['pinfi'] for t in tools])
    ax.set(xticks=x, ylabel='Execution time\nnorm. to PINFI')#, title=app)
    ax.set_xticklabels([t[0:7].upper() for t in tools], rotation='vertical')
    rects = plt.bar(x, y, color=tableau20blind[0])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    autolabel(width, ax, rects, 0)
    plt.savefig(app+'-time-norm.eps', bbox_inches='tight')
    plt.close()

matplotlib.rcParams.update({'font.size': 24})
fig, ax = plt.subplots()
x = range(0, len(args.tools))
y = np.array([total_timings[t]/3600.0 for t in args.tools])
ax.set(xticks=x, ylabel='Time (h)')#, title=app)
ax.set_xticklabels([t[0:7].upper() for t in args.tools], rotation='vertical')
rects = plt.bar(x, y, color=tableau20blind[0])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
autolabel(width, ax, rects, 0)
plt.savefig('total-time.eps', bbox_inches='tight')
plt.close()

matplotlib.rcParams.update({'font.size': 32})
fig, ax = plt.subplots()
# copy list
tools = args.tools[:]
# remove pinfi used for norm
tools.remove('pinfi')
x = range(0, len(tools))
y = np.array([total_timings[t]/total_timings['pinfi'] for t in tools])
ax.set(xticks=x, ylabel='Execution time\nnorm. to PINFI')#, title=app)
ax.set_xticklabels([t[0:7].upper() for t in tools], rotation='vertical')
rects = plt.bar(x, y, color=tableau20blind[0])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
autolabel(width, ax, rects, 0)
plt.savefig('total-time-norm.eps', bbox_inches='tight')
plt.close()

