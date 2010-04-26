from __future__ import with_statement # with statement in Python 2.5

# matlab.py:  Matlab extension builder
# 
# by Marc Joliet, marcec@gmx.de, 2010.04.22
# (loosely based on mex.py by Joe VanAndel, vanandel@ucar.edu, 2010/1/15)
#
# This is a little SCons builder tool that finds Matlabs installation directory
# and sets various variables of the build environment. To do that, it starts a
# Matlab subprocess that issues a few commands that print to a file, and parses
# the file.
#
# TODO: Find out if results can be cached. As a workaround, use interactive mode
# and use the "build" command (short form "b").

import os, tempfile, subprocess as subp, sys

def generate(env, **kwargs):
    # determine if the env is supposed to be a mex extension, default to False
    is_mex_ext = kwargs.get('mex', False)

    tmp_file, tmp_file_name = tempfile.mkstemp()
    # As per Python tempfile documentation, Windows doesn't support multiple
    # processes accessing the same file, so close it immediately.
    os.close(tmp_file)

    # Invoke matlab, method of doing so taken from the mlabwrap setup.py.  The
    # usage of '10' as a newline char is needed because... maybe Python
    # universal newlines translate to newlines Matlab doesn't like? I dunno, but
    # in the Matlab command line '\n' works, but not in this script, even with
    # escapes or as a raw string.
    matlab_cmd = "fid = fopen('%s', 'wt');" % tmp_file_name + \
            r"fprintf(fid, '%s%c%s%c%s%c', mexext, 10, matlabroot, 10, computer, 10);" + \
            "fclose(fid);quit;"
    cmd_line = ['matlab', '-nodesktop', '-nosplash', '-r', matlab_cmd]
    if os.name == "nt":
        matlab_cmd[-1] = '"' + matlab_cmd[-1] + '"'
        matlab_cmd += ['-wait'] # stop Matlab from forking

    try:
        # output to pipe to suppress output on Unix
        subp.check_call(cmd_line, stdout=subp.PIPE)
    except BaseException, e:
        # PEP 352 can't go ahead quickly enough, stupid args tuple. I want the
        # message attribute back!
        print >> sys.stderr, "Error:", ', '.join([repr(i) for i in e.args])
        os.remove(tmp_file_name)
        exit("Error calling Matlab, exiting.")

    # read lines from file and remove newline chars
    with open(tmp_file_name) as tmp_file:
        lines = [l.strip('\n') for l in tmp_file.readlines()]
    os.remove(tmp_file_name)

    matlab_root = lines[1]
    matlab_arch = lines[2].lower()
    if matlab_arch == 'pcwin':
        matlab_arch = 'win32'
    env['MATLAB'] = {
            "MEX_EXT":  "." + lines[0],
            "ROOT":     matlab_root,
            "ARCH":     matlab_arch,
            "SRC":      os.sep.join([matlab_root, 'extern', 'src']),
            "INCLUDE":  os.sep.join([matlab_root, 'extern', 'include']),
            "LIB_DIR":  [os.sep.join([matlab_root, 'bin', matlab_arch])]
            }
    if matlab_arch == 'pcwin':
        env['MATLAB']['LIB_DIR'] += [os.sep.join(
            [matlab_root, 'extern', 'lib', 'win32', 'microsoft'])]

    env.Append(CPPPATH = [env['MATLAB']['INCLUDE']],
            LIBPATH = [env['MATLAB']['LIB_DIR']])

    if is_mex_ext:
        env.Replace(SHLIBPREFIX="", SHLIBSUFFIX=env['MATLAB']['MEX_EXT'])
        env.Append(CPPDEFINES=["MATLAB_MEX_FILE"])

def exists(env):
    # FIXME: Why is this function not called? Calling exit() here does nothing!
    if not env.WhereIs("matlab"):
        return False
    return True
