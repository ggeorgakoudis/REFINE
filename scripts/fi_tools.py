import data
import sys
import random
import os
import re
import subprocess

pindir = os.environ['PINDIR']
pinbin = pindir + 'pin'

files = {
'instcount' : { 'llfi' : 'llfi.stat.prof.txt', 'pinfi' : 'pin.instcount.txt', 'refine' : 'refine-inscount.txt', 'refine-mbb' : 'refine-inscount.txt' },
'injection' : { 'llfi' : 'llfi.stat.fi.injectedfaults.txt', 'pinfi':'pin.injection.txt', 'refine':'refine-inject.txt', 'refine-mbb':'refine-inject.txt' },
}

def get_profbin(appsdir, tool, app):
    workdir = appsdir + '/' + tool + '/'
    if tool == 'refine' or tool == 'refine-mbb' or tool == 'pinfi':
        profbin = workdir + data.execs[app][0]
    elif tool == 'llfi':
        # special fix for NAS benchmarks
        if app in data.NAS.keys():
            # add class to the path
            LLFIDIR = workdir + data.NASBASEDIR + app + '/llfi-' + data.NAS[app]['CLASS'] + '/'
            # remove .x from exec filename
            profbin = LLFIDIR + os.path.basename(data.execs[app][0][:-2])+'-profiling.exe'
        else:
            # fix for CoMD
            if app == 'CoMD':
                profbin = workdir + data.dirs[app]['build']['dir'] + '/llfi/' +  os.path.basename(data.execs[app][0])+'-profiling.exe'
            else:
                profbin = workdir + os.path.dirname(data.execs[app][0]) + '/llfi/' +  os.path.basename(data.execs[app][0])+'-profiling.exe'
    else:
        print('Invalid tool: ' + tool)
        sys.exit(1)

    return profbin

def get_fibin(appsdir, tool, app):
    workdir = appsdir + '/' + tool + '/'
    if tool == 'refine' or tool == 'refine-mbb' or tool == 'pinfi':
        fibin = workdir + data.execs[app][0]
    elif tool == 'llfi':
    # special fix for NAS benchmarks
        if app in data.NAS.keys():
            # add class to the path
            LLFIDIR = workdir + data.NASBASEDIR + app + '/llfi-' + data.NAS[app]['CLASS'] + '/'
            # remove .x from exec filename
            fibin = LLFIDIR + os.path.basename(data.execs[app][0][:-2])+'-faultinjection.exe'
        else:
            # fix for CoMD
            if app == 'CoMD':
                fibin = workdir + data.dirs[app]['build']['dir'] + '/llfi/' + os.path.basename(data.execs[app][0])+'-faultinjection.exe'
            else:
                fibin = workdir + os.path.dirname(data.execs[app][0]) + '/llfi/' + os.path.basename(data.execs[app][0])+'-faultinjection.exe'
    else:
        print('Invalid tool: ' + tool)
        sys.exit(1)
    return fibin

def get_prof_execlist(appsdir, tool, app):
    execlist = [get_profbin(appsdir, tool, app)] + data.execs[app][1:]
    if tool == 'refine' or tool == 'refine-mbb':
        pass
    elif tool == 'pinfi' or tool == 'pinfi-unopt':
        instcountlib = pindir +'source/tools/'+tool+'/obj-intel64/instcount'
        execlist = [pinbin, '-t', instcountlib, '--'] + execlist
    elif tool == 'llfi':
        pass
    else:
        print('Invalid tool: ' + tool)
        sys.exit(1)
    return execlist

def get_fi_execlist(appsdir, tool, app):
    execlist = [get_fibin(appsdir, tool, app)] + data.execs[app][1:]
    if tool == 'refine' or tool == 'refine-mbb':
        pass
    elif tool == 'pinfi' or tool == 'pinfi-unopt':
        filib = pindir + 'source/tools/'+tool+'/obj-intel64/faultinjection'
        execlist = [pinbin, '-t', filib, '--'] + execlist
    elif tool == 'llfi':
        pass
    else:
        print('Invalid tool: ' + tool)
        sys.exit(1)
    return execlist

def setup(tool, app, appsdir, trialdir):
    if tool == 'refine' or tool == 'refine-mbb' or tool == 'pinfi':
        pass
    elif tool == 'llfi':
        path = os.getcwd()
        instcount = 0

        os.chdir(appsdir + '/llfi/' + data.dirs[app]['appdir'])
        with open('llfi.stat.prof.txt', 'r') as f:
            s = f.read()
            m = re.search('total_cycle=(\d+)\s+', s)
            instcount = int(m.group(1))

        assert instcount > 0, 'Instcount: ' + str(instcount) + ' is invalid!'

        os.chdir(trialdir)
        with open('llfi.config.runtime.txt', 'w') as f:
            fi_cycle = random.randint(0, int(instcount) - 1)
            f.write('fi_cycle=' + str(fi_cycle) + '\n')
            f.write('fi_type=bitflip\n')

        os.chdir(path)
    else:
        print('Invalid tool: ' + tool)
        sys.exit(1)

    if not os.path.isfile(trialdir + '/' + files['instcount'][tool]):
        os.symlink(appsdir +'/'+tool+'/'+ data.dirs[app]['appdir'] + '/' + files['instcount'][tool], trialdir + '/' + files['instcount'][tool])
    for f in data.ifiles[app]:
        # XXX: os.path.exists as it can be a file or a dir
        if not os.path.exists(trialdir + '/' + f):
            os.symlink(appsdir +'/'+tool+'/'+ data.dirs[app]['appdir'] + '/' + f, trialdir + '/' + f)

def cleanup(tool, app, appsdir, trialdir):
    if data.cleanup[app]:
        path = os.getcwd()
        os.chdir(trialdir)
        subprocess.run(data.cleanup[app], shell=True)
        os.chdir(path)

