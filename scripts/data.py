import os
import sys

try:
    appsdir = os.environ['APPSDIR']
except:
    print('Env variable APPSDIR is missing')
    sys.exit(1)


## XXX: IS is very short running and it has no output to verify
## XXX: MG fails to compile for any CLASS >B, linker error, otherwise too short
NAS = { 'BT':{ 'CLASS':'A' }, 'CG':{ 'CLASS':'B' }, 'DC': { 'CLASS':'W' }, 'EP': { 'CLASS':'A' },
        'FT':{ 'CLASS':'B' }, 'IS':{ 'CLASS':'A' }, 'LU': { 'CLASS':'A' }, 'MG': { 'CLASS':'B' },
        'SP':{ 'CLASS':'A' }, 'UA':{ 'CLASS':'B' }}

#NAS = { 'BT':{ 'CLASS':'S' }, 'CG':{ 'CLASS':'S' }, 'DC': { 'CLASS':'S' }, 'EP': { 'CLASS':'S' },
#        'FT':{ 'CLASS':'S' }, 'IS':{ 'CLASS':'S' }, 'LU': { 'CLASS':'S' }, 'MG': { 'CLASS':'S' },
#        'SP':{ 'CLASS':'S' }, 'UA':{ 'CLASS':'S' }}

NASBASEDIR = 'NPB3.3-SER-C/'

EXPFLOAT = r'[+-]?\d+\.\d+[Ee][+-]?\d+'
FLOAT = r'[+-]?\d+\.\d+'

dirs = {
'AMG2013': { 'appdir':'AMG2013/test/', 'build':{ 'dir':'AMG2013/', 'args':[] } },
'CoMD': { 'appdir':'CoMD/', 'build':{ 'dir':'CoMD'+'/src-mpi/', 'args':[] } },
'HPCCG-1.0': { 'appdir':'HPCCG-1.0/', 'build':{ 'dir':'HPCCG-1.0/', 'args':[] } },
'lulesh': { 'appdir':'lulesh/', 'build':{ 'dir':'lulesh/', 'args':[] } },
'XSBench': { 'appdir':'XSBench/src/', 'build':{ 'dir':'XSBench/src/', 'args':[] } },
'miniFE': { 'appdir':'miniFE/ref/src/', 'build':{ 'dir':'miniFE/ref/src/', 'args':[] } },
'BT': { 'appdir':NASBASEDIR+'BT/', 'build':{ 'dir':NASBASEDIR+'BT/', 'args':['BT','CLASS='+NAS['BT']['CLASS']] } },
'CG': { 'appdir':NASBASEDIR+'CG/', 'build':{ 'dir':NASBASEDIR+'CG/', 'args':['CG','CLASS='+NAS['CG']['CLASS']] } },
'DC': { 'appdir':NASBASEDIR+'DC/', 'build':{ 'dir':NASBASEDIR+'DC/', 'args':['DC','CLASS='+NAS['DC']['CLASS']] } },
'EP': { 'appdir':NASBASEDIR+'EP/', 'build':{ 'dir':NASBASEDIR+'EP/', 'args':['EP','CLASS='+NAS['EP']['CLASS']] } },
'FT': { 'appdir':NASBASEDIR+'FT/', 'build':{ 'dir':NASBASEDIR+'FT/', 'args':['FT','CLASS='+NAS['FT']['CLASS']] } },
'LU': { 'appdir':NASBASEDIR+'LU/', 'build':{ 'dir':NASBASEDIR+'LU/', 'args':['LU','CLASS='+NAS['LU']['CLASS']] } },
'SP': { 'appdir':NASBASEDIR+'SP/', 'build':{ 'dir':NASBASEDIR+'SP/', 'args':['SP','CLASS='+NAS['SP']['CLASS']] } },
'UA': { 'appdir':NASBASEDIR+'UA/', 'build':{ 'dir':NASBASEDIR+'UA/', 'args':['UA','CLASS='+NAS['UA']['CLASS']] } },
}

execs = {
'AMG2013':['/AMG2013/test/amg2013', '-in', 'sstruct.in.MG.FD', '-r', '24', '24', '24'],
#'AMG2013': [ 'AMG2013/test/amg2013', '-in', 'sstruct.in.MG.FD', '-r', '8', '8', '8'],
'CoMD':['/CoMD/bin/CoMD-serial', '-d', './pots/', '-e', '-i', '1', '-j', '1', '-k', '1', '-x', '32', '-y', '32', '-z', '32'],
#'CoMD':['/CoMD/bin/CoMD-serial', '-d', './pots/', '-e', '-i', '1', '-j', '1', '-k', '1', '-x', '4', '-y', '4', '-z', '4'],
'HPCCG-1.0':['HPCCG-1.0/test_HPCCG', '128', '128', '128'],
#'HPCCG-1.0':['HPCCG-1.0/test_HPCCG', '32', '32', '32'],
'lulesh':['lulesh/lulesh2.0'],
#'lulesh':['lulesh/lulesh2.0', '-i', '10'],
'XSBench':['/XSBench/src/XSBench','-s','small'],
#'XSBench':['/XSBench/src/XSBench','-s','small', '-l', '100000'],
'miniFE':['/miniFE/ref/src/miniFE.x','-nx','66','-ny','64','-nz','64'],
#'miniFE':['/miniFE/ref/src/miniFE.x','-nx','18','-ny','16','-nz','16'],
'BT':[NASBASEDIR+'bin/bt.'+NAS['BT']['CLASS']+'.x'],
'CG':[NASBASEDIR+'bin/cg.'+NAS['CG']['CLASS']+'.x'],
'DC':[NASBASEDIR+'bin/dc.'+NAS['DC']['CLASS']+'.x'],
'EP':[NASBASEDIR+'bin/ep.'+NAS['EP']['CLASS']+'.x'],
'FT':[NASBASEDIR+'bin/ft.'+NAS['FT']['CLASS']+'.x'],
'LU':[NASBASEDIR+'bin/lu.'+NAS['LU']['CLASS']+'.x'],
'SP':[NASBASEDIR+'bin/sp.'+NAS['SP']['CLASS']+'.x'],
'UA':[NASBASEDIR+'bin/ua.'+NAS['UA']['CLASS']+'.x'],
}

ifiles = {
'AMG2013': [ 'sstruct.in.MG.FD'],
# it's actually a dir
'CoMD' : [ 'pots' ],
'HPCCG-1.0' : [],
'lulesh' : [],
'XSBench' : [],
'miniFE' : [],
'BT' : [],
'CG': [],
'DC' : [],
'EP' : [],
'FT' : [],
'LU' : [],
'SP' : [],
'UA' : []
}

# Ths will run in a shell=True subprocess
cleanup = {
'AMG2013': '',
'CoMD' : '/bin/rm -rf CoMD*yaml',
'HPCCG-1.0' : '/bin/rm -rf hpccg*yaml',
'lulesh' : '',
'XSBench' : '',
'miniFE' : '/bin/rm -rf miniFE*yaml',
'BT' : '',
'CG': '',
'DC' : '/bin/rm -rf ADC.*',
'EP' : '',
'FT' : '',
'LU' : '',
'SP' : '',
'UA' : ''
}

verify = {
'AMG2013' :['Final Relative Residual Norm = ' + EXPFLOAT],
'CoMD': ['Final energy\s+: ' + FLOAT, 'Final atom count : \d+, no atoms lost' ],
'HPCCG-1.0':['Final residual: : ' + EXPFLOAT ],
'lulesh':['Final Origin Energy = ' + EXPFLOAT ],
'XSBench':['Verification checksum: 74966788162'],
'miniFE':['Final Resid Norm: ' + EXPFLOAT],
'BT':['\d\s+' + EXPFLOAT +' ' + EXPFLOAT + ' ' + EXPFLOAT],
'CG':[' Zeta\s+' + EXPFLOAT],
'DC':['Checksum\s+=\s+' + EXPFLOAT],
'EP':['Sums =\s+' + EXPFLOAT + '\s+' + EXPFLOAT],
'FT':['T =\s+\d+\s+Checksum =\s+' + EXPFLOAT + '\s+' + EXPFLOAT],
'LU': ['\d\s+' + EXPFLOAT +' ' + EXPFLOAT + ' ' + EXPFLOAT, '\s+' + EXPFLOAT +' ' + EXPFLOAT + ' ' + EXPFLOAT, ],
'SP':['\d\s+' + EXPFLOAT +' ' + EXPFLOAT + ' ' + EXPFLOAT],
'UA':['\s+' + EXPFLOAT +' ' + EXPFLOAT + ' ' + EXPFLOAT, ],
}

