import os
import data
import fi_tools

def pending_exps(appsdir, tool, app, start, end):
    cwd = os.getcwd()
    rem = []
    #print('Tool: ' + tool)
    mis_exps = 0
    nil_exps = 0
    nil_injs = 0
    mis_injs = 0
    n_timeout = 0

    appsdir = os.environ['APPSDIR'] + tool + '/'
    os.chdir(appsdir + data.dirs[app]['appdir'])
    for idx in range(start, end+1):
        trialdir = appsdir + data.dirs[app]['appdir'] + tool + '/' + str(idx) + '/'
        try:
            os.chdir(trialdir)
        except FileNotFoundError:
            mis_exps += 1
            rem.append(idx)
            continue
            #print('Missing exp: ' + tool + ' ' + app + ' ' + str(idx))
        try:
            ret_file = open('ret.txt', 'r')
        except FileNotFoundError:
            #print('Nil exp: ' + tool + ' ' + app + ' ' + str(idx))
            nil_exps += 1
            rem.append(idx)
            continue

        try:
            if os.stat(fi_tools.files['injection'][tool]).st_size == 0:
                #print('Nil injection: ' + tool + ' ' + app + ' ' + str(idx) + ', ret: ' + ret_file.readline().rstrip())
                nil_injs += 1
                rem.append(idx)
                # XXX: remove ret.txt to trigger rer-un
                os.remove('ret.txt')
        except FileNotFoundError:
            #print('Missing injection: ' + tool + ' ' + app + ' ' + str(idx)  + ', ret:' + ret_file.readline().rstrip())
            mis_injs += 1
            rem.append(idx)
            # XXX: remove ret.txt to trigger re-run
            os.remove('ret.txt')

        try:
            ret_file = open('ret.txt', 'r')
        except FileNotFoundError:
            print('Missing exp: ' + tool + ' ' + app + ' ' + str(i))
            continue
        res = ret_file.read()
        res = res.strip().split(',')
        if res[0] == 'timeout':
            n_timeout += 1
    print('\tapp: ' + app + ', missing exps: ' + str(mis_exps) + ', nil exps: ' + str(nil_exps) + ', missing injs: ' + str(mis_injs) + ', nil injs: ' + str(nil_injs)+', timeouts: ' + str(n_timeout))
    os.chdir(cwd)
    return rem

