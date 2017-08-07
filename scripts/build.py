import subprocess
import timeit
import sys

def make(workdir, args):
    out = open('compile-out.txt', 'w')
    err = open('compile-err.txt', 'w')
    p = subprocess.Popen(['make'] + args, stdout = out, stderr = err, cwd = workdir)
    p.wait()
    if p.returncode == 0:
        print('make succeeded')
    else:
        print('make failed!')
        sys.exit(p.returncode)

def build(workdir, args):
    p = subprocess.Popen(['make', 'clean'], cwd = workdir)
    p.wait()
    if p.returncode == 0:
        print('make clean succeeded')
    else:
        print('make clean failed!')
        sys.exit(p.returncode)

    t = timeit.repeat(lambda: make(workdir, args), number = 1, repeat = 1)
    timing_file = open('compile-time.txt', 'w')
    timing_file.write('%.2f'%min(t) + '\n')

