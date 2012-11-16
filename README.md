An SCons Tool for Matlab
========================
Marc Joliet <marcec@gmx.de>

Introduction
------------

This is an SCons extension (more precisely, a tool) for compiling Mex extensions
and programs that call to the Matlab engine.  It adds a 'MATLAB' `dict` to your
build systems env that contains potentially interesting information, e.g., you
can get Matlabs library directory via `env["MATLAB"]["LIB_DIR"]`.  More
importantly, it defines a `Mex()` pseudo-builder that wraps the `SharedLibrary`
builder.

The `Mex()` pseudo-builder takes care of the following:

- adding necessary compiler options
- adding the minimal set of necessary linker options (see Usage below)
- automatically adding `mexversion.c` (`mexversion.rc` on Windows) to the source
  file list (for older Matlab versions).

Installation
------------

The SCons Matlab tool depends on

- Python (2.5 or newer)
- SCons (obviously)
- Matlab (the earliest version I tested with is R2007a)

If you use git, installation is easy: you just add this repository as a git
submodule in the `site_scons/site_tools` directory, e.g., in `matlab`.

If you don't use git, copy the repository to your projects
`site_scons/site_tools` directory into a subdirectory with a sensible name,
e.g., in `matlab`.

Usage
-----

Use this as you would any other SCons extension: add it to the `tools` argument
of `Environment()`, for example:

    env = Environment(tools = ['default', 'matlab'])

To compile a Mex source file, use the method `Mex()`, like so:

    mex_ext = env.Mex("mex_ext", ["mex_ext.c"])

`Mex()` takes care of adding necessary compiler options (e.g., `-fexception`) and
linker options (e.g., `-lmx`).

NOTE: `Mex()` intends to only do the minimal amount of necessary work, that is, it
does not do things that are unnecessary for a minimal Mex file.  For instance,
it links to the smallest possible set of libraries (i.e., mex and mx).
Therefor, if you use Matlab libraries other than mx and mex, you need to link to
them yourself.

NOTE: On first run, Matlab must be started.  The values stored in
`env['MATLAB']` are static per Matlab installation, and are cached.  If you
change your Matlab installation, you can delete the file `.matlab_vars_cache` to
update the information.

License
-------

See the file LICENSE.
