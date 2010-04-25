# matlab.py:  Matlab extension builder
# 
# by Marc Joliet, marcec@gmx.de, 2010.04.22
# (based on mex.py by Joe VanAndel, vanandel@ucar.edu, 2010/1/15)
#
# This is a little SCons builder tool that finds Matlabs installation directory
# and sets various variables of the build environment. To do that, it starts a
# Matlab subprocess, issues a few commands, and parses the result.
#
# NOTE: This only works on Unix, as Matlab under Windows doesn't work with pipes
#
# TODO: find out if results can be cached

import os, re
from subprocess import Popen, PIPE

def generate(env):
    # invoke matlab
    proc = Popen(['matlab', '-nosplash'], stdin=PIPE, stdout=PIPE)

    # get mex extension, matlab installation root and Matlab arch
    stdout, stderr = proc.communicate('\n'.join( ['mexext', 'matlabroot',
        "getenv('MATLAB_ARCH')", 'quit']))

    # get lines not starting with space or newline, and empty lines
    pat   = re.compile("^(\s+.*)*$")
    lines = [l for l in stdout.split('\n') if not pat.findall(l)]

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
