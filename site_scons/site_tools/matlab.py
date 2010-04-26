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
# TODO: find out if results can be cached. as a workaround, use interactive mode
# and use the "build" command (short form "b").

import os, tempfile, subprocess as subp, sys

def generate(env, **kwargs):
    # determine if the env is supposed to be a mex extension, default to False
    is_mex_ext = kwargs.get('mex', False)

    # invoke matlab, method of doing so taken from the mlabwrap setup.py
    with tempfile.NamedTemporaryFile() as tmp_file:
        # The usage of '10' as a newline char is needed because... maybe Python
        # universal newlines translate to newlines Matlab doesn't like? I dunno, but
        # in the Matlab command line '\n' works, but not in this script, even with
        # escapes or as a raw string.
        matlab_cmd = "fid = fopen('%s', 'wt');" % tmp_file.name + \
                r"fprintf(fid, '%s%c%s%c%s%c', mexext, 10, matlabroot, 10, computer, 10);" + \
                "fclose(fid);quit;"
        if os.name == "nt":
            matlab_cmd = '"' + matlab_cmd + '"'
        cmd_line = ['matlab', '-nodesktop', '-nosplash', '-r', matlab_cmd]

        try:
            # output to pipe to suppress output on Unix
            subp.check_call(cmd_line, stdout=subp.PIPE)
        except (OSError, subp.CalledProcessError) as e:
            # PEP 352 can't go ahead quick enough, stupid args tupel. I want the
            # message attribute back!
            print >> sys.stderr, "Error:", ', '.join([repr(i) for i in e.args])
            exit("Error calling Matlab!")

        # read lines from file and remove newline chars
        lines = [l.strip('\n') for l in tmp_file.file.readlines()]

    matlab_root = lines[1]
    matlab_arch = lines[2].lower()
    env['MATLAB'] = {
            "MEX_EXT":  "." + lines[0],
            "ROOT":     matlab_root,
            "ARCH":     matlab_arch,
            "SRC":      ''.join([matlab_root, os.sep, 'extern', os.sep, 'src']),
            "INCLUDE":  ''.join([matlab_root, os.sep, 'extern', os.sep, 'include']),
            "LIB_DIR":  ''.join([matlab_root, os.sep, 'bin', os.sep, matlab_arch])
            }
    env.Append(CPPPATH = [env['MATLAB']['INCLUDE']],
            LIBPATH = [env['MATLAB']['LIB_DIR']])

    if is_mex_ext:
        env.Replace(SHLIBPREFIX="", SHLIBSUFFIX=env['MATLAB']['MEX_EXT'])
        env.Append(CPPDEFINES=["MATLAB_MEX_FILE"])

def exists(env):
    # FIXME: why is this function not called? Calling exit() here does nothing!
    if not env.WhereIs("matlab"):
        return False
    return True
