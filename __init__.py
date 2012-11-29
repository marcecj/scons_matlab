from __future__ import with_statement # with statement in Python 2.5

# mex_builder.py:  Matlab extension builder
#
# by Marc Joliet, marcec@gmx.de, 2010.04.22
# (loosely based on mex.py by Joe VanAndel, vanandel@ucar.edu, 2010/1/15)
#
# This is a little SCons builder tool that finds Matlabs installation directory
# and sets various variables of the build environment. To do that, it starts a
# Matlab subprocess that issues a few commands that print to a file, and parses
# the file.  Furthermore, it adds a pseudo-builder method to the environment
# that wraps the SharedLibrary builder.

import os
import subprocess as subp
import sys
import pickle

# Windows only: catches Matlabs output, since you cannot print to stdout
_matlab_log_file = '.matlab_output'

# caches the Matlab variables
_vars_file = '.matlab_vars_cache'

def _load_matlab_vars(env):
    """Load various Matlab specific variables from a cache file via the pickle
    module.
    """

    with open( _vars_file, 'r' ) as f:
        p = pickle.Unpickler(f)
        env['MATLAB'] = p.load()

def _cache_matlab_vars(matlab_vars):
    """Store various Matlab specific variables in a cache file via the pickle
    module.
    """

    # store the objects in a file
    with open(_vars_file, 'w') as f:
        p = pickle.Pickler(f)
        p.dump(matlab_vars)

def _gen_matlab_env(env, **kwargs):
    """Obtain various Matlab specific variables and put them in env['MATLAB'].
    """

    if os.path.isfile(_vars_file):
        if not env.GetOption('silent'):
            print "Loading Matlab vars from cache..."
        _load_matlab_vars(env)
        return

    # invoke matlab and print required information
    matlab_cmd = r"fprintf(1, '%s\n%s\n%s\n', mexext, matlabroot, computer('arch'), version); quit;"

    cmd_line = ['matlab', '-nodesktop', '-nosplash']

    if os.name == "nt":
        cmd_line += ['-r', '"' + matlab_cmd + '"']
        # stop Matlab from forking and output to a log file
        cmd_line += ['-wait', '-logfile', _matlab_log_file]

    try:
        # open a Matlab subprocess that communicates over pipes
        matlab_proc = subp.Popen(cmd_line, stdin=subp.PIPE, stdout=subp.PIPE)

        # capture Matlabs stdout
        mlab_out = matlab_proc.communicate(matlab_cmd)[0]

    except BaseException, e:

        # PEP 352 can't go ahead quickly enough, stupid args tuple. I want the
        # message attribute back!
        print >> sys.stderr, "Error:", ', '.join([repr(i) for i in e.args])

        exit("Error calling Matlab, exiting.")

    if os.name == 'nt':
        with open(_matlab_log_file) as mlab_out:
            mlab_out = mlab_out.readlines()[-4::]
    else:
        # everything before the first input line can be ignored
        # NOTE: I'm not sure, but I think you can't change the '>>' string, so this
        # should be reliable
        mlab_out = mlab_out.split('>>')[-1].split('\n')

    # save non-empty lines from stdout and strip surrounding whitespace
    lines = [l.strip() for l in mlab_out if len(l)>0]

    matlab_root = lines[1]
    matlab_arch = lines[2].lower()
    matlab_ver, matlab_release  = lines[3].split()

    env['MATLAB'] = {
        "MEX_EXT":  "." + lines[0],
        "ROOT":     matlab_root,
        "ARCH":     matlab_arch,
        "VERSION":  matlab_ver,
        "RELEASE":  matlab_release.strip('()'),
        "SRC":      os.sep.join([matlab_root, 'extern', 'src']),
        "INCLUDE":  os.sep.join([matlab_root, 'extern', 'include']),
        "LIB_DIR":  [os.sep.join([matlab_root, 'bin', matlab_arch])]
    }

    if matlab_arch == 'win32':
        env['MATLAB']['LIB_DIR'] += \
                [os.sep.join([matlab_root, 'extern', 'lib', 'win32', 'microsoft'])]

    print "Caching Matlab vars..."
    _cache_matlab_vars(env['MATLAB'])

def _mex_builder(env, target, source, gen_def=False, **kwargs):
    """A Mex pseudo-builder for SCons that wraps the SharedLibrary builder.

       This pseudo-builder merely inserts some library dependencies, source file
       dependencies and the compiler expected by Matlab.  We don't return the
       targets and sources, since they only change on Unix, where we don't do
       anything but build anyway.
       """

    source   = list(source)
    platform = env['PLATFORM']

    # define operating system independent options and dependencies
    if platform == "win32":
        # Matlab doesn't follow the Windows standard and adds a 'lib' prefix anyway
        env.AppendUnique(LIBS = ["libmex", "libmx"])
    else:
        env.AppendUnique(LIBS = ["mex", "mx"])

    # OS dependent stuff, we assume GCC on Unix like platforms
    if platform in ("posix", "darwin"):

        # add "exceptions" option, without which any mex function that raises an
        # exception (e.g., mexErrMsgTxt()) causes Matlab to crash
        env.AppendUnique(CCFLAGS=["-fexceptions", "-pthread"])

    elif platform == "win32":

        if gen_def:
            env.Replace(WINDOWS_INSERT_DEF = True)

            # add the Textfile builder to the build environment
            env.Tool('textfile')

            # generate a .def file
            env.Textfile(target,
                         source=["LIBRARY " + [s for s in source if target in s][0],
                                 "EXPORTS mexFunction"],
                         TEXTFILESUFFIX='.def')

    else:
        exit("Oops, not a supported platform.")

    # the need for mexversion.c was removed in Matlab version 7.9
    if env['MATLAB']['RELEASE'] < "R2009a":

        # give each Mex file its own mexversion object (prevents warnings
        # from SCons and makes sure the same compiler options are used)
        mexversion = env.Clone()

        if os.name == 'nt':
            mexversion_obj = mexversion.RES("mexversion_" + target,
                                            os.sep.join([env['MATLAB']['INCLUDE'],
                                                        "mexversion.rc"]))
        else:
            mexversion_obj = mexversion.SharedObject("mexversion_" + target,
                                                     os.sep.join([env["MATLAB"]["SRC"],
                                                         "mexversion.c"]))

        source.append(mexversion_obj)

    env.AppendUnique(CPPDEFINES = ["MATLAB_MEX_FILE"],
                     CPPPATH    = [env['MATLAB']['INCLUDE']],
                     LIBPATH    = [env['MATLAB']['LIB_DIR']])

    # add compile target: return the node object
    return env.SharedLibrary(target, source,
                             SHLIBPREFIX="",
                             SHLIBSUFFIX=env['MATLAB']['MEX_EXT'],
                             **kwargs)

def generate(env, **kwargs):
    _gen_matlab_env(env, **kwargs)

    # add the Mex pseudo-builder to the environment
    # NOTE: adding the function to $BUILDERS wraps it in a BuilderMethod object,
    # which gives it the calling conventions of regular builders.
    env['BUILDERS']['Mex'] = _mex_builder

def exists(env):
    # FIXME: Why is this function not called? Calling exit() here does nothing!
    if not env.WhereIs("matlab"):
        return False
    return True
