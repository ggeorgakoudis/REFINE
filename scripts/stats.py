#!/usr/bin/env python3

import os
import data
import fi_tools
import argparse
import re
import sys
import matplotlib.pyplot as plt

try:
    appsdir = os.environ['APPSDIR']
except:
    print('Env variable APPSDIR is missing')
    sys.exit(1)

parser = argparse.ArgumentParser('This script create plots')
parser.add_argument('tools', help='tools list to experiment', nargs='+')
parser.add_argument('start', help='start trial', type=int)
parser.add_argument('end', help='end trial', type=int)
args = parser.parse_args()

apps = [ 'AMG2013' , 'CoMD', 'HPCCG-1.0', 'XSBench', 'miniFE', 'lulesh', 'BT', 'CG', 'DC', 'EP', 'FT', 'LU', 'SP', 'UA' ]

for tool in args.tools:
    for app in apps:
        bits={}
        fi=[]
        for idx in range(args.start, args.end+1):
            trialdir = appsdir + tool + '/' +  data.dirs[app]['appdir'] + tool + '/' + str(idx) + '/'
            with open(trialdir+fi_tools.files['injection'][tool], 'r') as f:
                log=f.readline()
                if tool == 'refine':
                    m=re.match('fi_index=(.*), op=.*, size=(.*), bitflip=(.*).*', log)
                    fi.append(int(m.group(1)))
                    size=int(m.group(2))*8
                    if not size in bits.keys():
                        bits[size]=[]
                    bits[size].append(int(m.group(3)))
                elif tool == 'pinfi':
                    m=re.match('fi_index=(.*), reg=(.*), bitflip=(.*), addr=.*', log)
                    fi.append(int(m.group(1)))
                    reg=m.group(2)
                    if reg[0] == 'x':
                        size=128
                    elif reg[0] == 'r':
                        size=64
                    elif reg[0] == 'e':
                        size=32
                    elif reg in ['al', 'bl', 'cl', 'dl', 'sil', 'dil', 'spl', 'bpl']:
                        size=8
                    else:
                        assert False, 'reg:'+reg+' is unknown'
                    if not size in bits.keys():
                        bits[size]=[]
                    bits[size].append(int(m.group(3)))
                else:
                    assert False, 'Tool not implemented yet'

        print(app+' '+tool+' '+'max fi: '+str(max(fi)))
        #print(bits) #ggout
        fig=plt.figure()
        plt.suptitle(app)
        for idx, k in enumerate(sorted(bits.keys())):
            #print(bits) #ggout
            fig.add_subplot(4, 1, idx+1)
            plt.title(k)
            n, bins, patches = plt.hist(bits[k], k)
            if idx == 1:
                plt.ylabel('Frequency')
            plt.xlabel('Bit')
            plt.grid(True)

        #plt.show()
        plt.tight_layout()
        plt.savefig(tool+'-'+app+'-bits.eps', bbox_inches='tight')
        plt.close()
        '''cont=input('Continue (y/n): ')
        while not cont in ['y', 'n']:
            cont=input('Continue (y/n): ')
        if cont == 'n':
            sys.exit(0)'''
