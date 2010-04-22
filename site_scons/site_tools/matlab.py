# matlab.py:  Matlab extension builder
# 
# by Marc Joliet, marcec@gmx.de, 2010.04.22
# (based on mex.py by Joe VanAndel, vanandel@ucar.edu, 2010/1/15)
#
# This is a little SCons builder tool that finds Matlabs installation directory
# and sets various variables of the build environment. To do that, it starts a
# Matlab subprocess, issues a few commands, and parses the result.
#
# TODO: find out if results can be cached

import os
import re
from subprocess import Popen,PIPE

def generate(env):
    # invoke matlab
    proc = Popen('matlab', stdin=PIPE, stdout=PIPE)

    # get mex extension, matlab installation root and Matlab arch
    os.write(proc.stdin.fileno(), "mexext\n")
    os.write(proc.stdin.fileno(), "matlabroot\n")
    os.write(proc.stdin.fileno(), "getenv('MATLAB_ARCH')\n")
    os.write(proc.stdin.fileno(), "quit\n")

    # get lines not starting with space or newline
    pat   = re.compile("^\s+.*$")
    lines = [l for l in proc.stdout.readlines() if not pat.findall(l)]

    # return value is every 3 lines: prompt, 'ans =', and then the actual answer
    matlab_root = lines[4].rstrip('\n')
    matlab_arch = lines[7].rstrip('\n')
    env['MATLAB'] = {
            "MEX_EXT":  "." + lines[1].rstrip('\n'),
            "ROOT":     matlab_root,
            "ARCH":     matlab_arch,
            "SRC":      ''.join([matlab_root, os.sep, 'extern', os.sep, 'src']),
            "INCLUDE":  ''.join([matlab_root, os.sep, 'extern', os.sep, 'include']),
            "LIB_DIR":  ''.join([matlab_root, os.sep, 'bin', os.sep, matlab_arch])
            }

    # TODO: maybe add option for the special case of Mex files instead of
    # assigning these Vars by default
    env.Replace(SHLIBPREFIX="", SHLIBSUFFIX=env['MATLAB']['MEX_EXT'])
    env.Append(
            CPPPATH     = [env['MATLAB']['INCLUDE']],
            LIBPATH     = [env['MATLAB']['LIB_DIR']],
            CPPDEFINES  = ["MATLAB_MEX_FILE"]
            )

def exists(env):
    # TODO: maybe add more tests here, don't know if we need them
    # TODO: add warning when Matlab doesn't exist
    if env.WhereIs("matlab") is None:
        return False
    return True
