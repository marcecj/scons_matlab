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

import os, tempfile, subprocess as subp, sys, pickle

vars_file = '.matlab_vars_cache'

def load_matlab_vars(env):
    """Load various Matlab specific variables from a cache file via the pickle
    module.
    """

    with open( vars_file, 'r' ) as f:
        p = pickle.Unpickler(f)
        env['MATLAB'] = p.load()

def cache_matlab_vars(matlab_vars):
    """Store various Matlab specific variables in a cache file via the pickle
    module.
    """

    # create the file if it doesn't exist
    if not os.path.isfile(vars_file):
        os.mknod(vars_file)

    # store the objects in a file
    with open(vars_file, 'w') as f:
        p = pickle.Pickler(f)
        p.dump(matlab_vars)

def gen_matlab_env(env, **kwargs):
    """Obtain various Matlab specific variables and put them in env['MATLAB'].
    """
    # determine if the env is supposed to be a mex extension, default to False
    is_mex_ext = kwargs.get('mex', False)

    if not os.path.isfile(vars_file):
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
                r"fprintf(fid, '%s%c%s%c%s%c', mexext, 10, matlabroot, 10, computer, 10, version, 10);" + \
                "fclose(fid);quit;"
        cmd_line = ['matlab', '-nodesktop', '-nosplash', '-r', matlab_cmd]
        if os.name == "nt":
            cmd_line[-1] = '"' + cmd_line[-1] + '"'
            cmd_line += ['-wait'] # stop Matlab from forking

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
        matlab_ver, matlab_release  = lines[3].split()
        if matlab_arch == 'pcwin':
            matlab_arch = 'win32'

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
            # TODO: test WINDOWS_INSERT_DEF option
            # env.Replace(WINDOWS_INSERT_DEF=True)

        print "Caching Matlab vars..."
        cache_matlab_vars(env['MATLAB'])
    else:
        print "Loading Matlab vars from cache..."
        load_matlab_vars(env)

    env.Append(CPPPATH = [env['MATLAB']['INCLUDE']],
            LIBPATH = [env['MATLAB']['LIB_DIR']])

    if is_mex_ext:
        env.Replace(SHLIBPREFIX="", SHLIBSUFFIX=env['MATLAB']['MEX_EXT'])
        env.Append(CPPDEFINES=["MATLAB_MEX_FILE"])

def mex_builder(env, target, source, only_deps=False, make_def=True):
    """A Mex pseudo-builder for SCons that wraps the SharedLibrary builder.

       This pseudo-builder merely inserts some library dependencies, source file
       dependencies and the compiler expected by Matlab.  We don't return the
       targets and sources, since they only change on Unix, where we don't do
       anything but build anyway.

       The only_deps option is for Windows, where a MSVS Solution file might be
       wanted, in which case only the dependencies are added to the environment.
       """

    # don't touch the original environment unless the dependencies are wanted;
    # this is supposed to prevent unwanted side effects (compiler options) when
    # adding Mex programs to existing environments
    if not only_deps:
        env = env.Clone()

    source   = list(source)
    platform = env['PLATFORM']

    # define operating system independent options and dependencies
    if platform == "win32":
        # Matlab doesn't follow the Windows standard and adds a 'lib' prefix anyway
        env.Append(LIBS = ["libmex", "libmx"])
    else:
        env.Append(LIBS = ["mex", "mx"])

    # this tells SCons where to find mexversion.c
    env.Repository(env["MATLAB"]["SRC"])

    # OS dependent stuff, we assume GCC on Unix like platforms
    if platform == "posix":
        # add "exceptions" option, without which any mex function that raises an
        # exception (e.g., mexErrMsgTxt()) causes Matlab to crash
        env.Append(CCFLAGS="-fexceptions -pthread")

        # the need for mexversion.c was removed in Matlab version 7.9
        if env['MATLAB']['RELEASE'] < "R2009a":
            mexversion = env.Clone()
            # give each Mex file its own mexversion object (prevents warnings
            # from SCons and makes sure the same compiler options are used)
            mexversion_obj = mexversion.SharedObject("mexversion_"+target,
                                                     "mexversion.c")
            source.append(mexversion_obj)
    elif platform == "win32":
        env.Append(WINDOWS_INSERT_MANIFEST = True)
        # TODO: test WINDOWS_INSERT_DEF option
        # def_file = env.Textfile(target+".def", \
        #     source=["LIBRARY " + [s for s in source if target in s],
        #             "EXPORTS mexFunction"])

        # source += [def_file]
    elif platform == "darwin":
        env.Append(CCFLAGS="-fexceptions -pthread")
    else:
        exit("Oops, not a supported platform.")

    # add compile target: return the node object (or None, if only the deps are
    # requested)
    if not only_deps:
        return env.SharedLibrary(target, source)
    else:
        return None

def generate(env, **kwargs):
    gen_matlab_env(env, mex=kwargs.get('mex', False))

    # defines a pseudo-builder that internally calls the SharedLibrary builder
    env.AddMethod(mex_builder, "MexExtension")

def exists(env):
    # FIXME: Why is this function not called? Calling exit() here does nothing!
    if not env.WhereIs("matlab"):
        return False
    return True
