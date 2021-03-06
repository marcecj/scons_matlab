An SCons Tool for MATLAB
========================
Marc Joliet <marcec@gmx.de>

Introduction
------------

This is an SCons tool for compiling Mex extensions and programs that call to the
MATLAB engine.  It adds a 'MATLAB' `dict` to your build systems env that
contains potentially interesting information, e.g., you can get MATLABs library
directory via `env["MATLAB"]["LIB_DIR"]`.  More importantly, it defines a
`Mex()` pseudo-builder that wraps the `SharedLibrary` builder.

The `Mex()` pseudo-builder takes care of the following:

- adding necessary compiler options
- adding the minimal set of necessary linker options (see Usage below)
- automatically adding `mexversion.c` (`mexversion.rc` on Windows) to the source
  file list (for older MATLAB versions).

Basically, it follows the guidelines in the section
"[Custom Building
MEX-Files](http://www.mathworks.de/de/help/matlab/matlab_external/custom-building-mex-files.html)"
of the MATLAB documentation.

Installation
------------

The SCons MATLAB tool depends on

- Python (2.5 or newer)
- SCons (obviously)
- MATLAB (the earliest version I tested with is R2007a)

If your project uses git, you could add this repository as a git submodule in
the `site_scons/site_tools` directory.  Otherwise, you can copy it there or
clone the repository into `$HOME/.scons/site_scons/site_tools` (or the
equivalent directory on Windows).  In all cases, the tool directory should be
named `matlab`.

Usage
-----

Use this as you would any other SCons extension: add it to the `tools` argument
of `Environment()`, for example:

    env = Environment(tools = ['default', 'matlab'])

To compile a Mex source file, use the method `Mex()`, like so:

    mex_ext = env.Mex("mex_ext", ["mex_ext.c"])

`Mex()` takes care of adding necessary compiler options (e.g., `-fexception`)
and linker options (e.g., `-lmx`).  Keep in mind, however, that `Mex()` intends
to only do the minimal amount of necessary work, that is, it does not do things
that are unnecessary for a minimal Mex file.  For instance, it links to the
smallest possible set of libraries (i.e., mex and mx).  Therefor, if you use
MATLAB libraries other than mx and mex, you need to link to them yourself.

It is also important to know that this builder modifies the environment it is
called from.  If this is undesirable, `Clone()`-ing the environment might be a
suitable workaround.

On first run, a MATLAB instance must be started.  The tool then stores the
following construction variables in `env['MATLAB']`:

- `MEX_EXT` -> The extension of MEX files on this computer.
- `ROOT`    -> MATLAB's installation location (e.g., `/usr/local/matlab/`).
- `ARCH`    -> MATLAB's architecture (e.g., "GLNX86").
- `VERSION` -> MATLAB's version (e.g., "7.10.0.499").
- `RELEASE` -> MATLAB's release (e.g., "R2010a").
- `SRC`     -> MATLAB's `src/` directory.
- `INCLUDE` -> MATLAB's `include/` directory.
- `LIB_DIR` -> The directory containing MATLAB's libraries.

These are static per MATLAB installation, and are cached via Python's `pickle`
module.  If you change your MATLAB installation, you can delete the file
`.matlab_vars_cache` to update the information.

Related Software
----------------

There is an alternative builder on the [SCons Wiki](http://www.scons.org/wiki/),
called [MexBuilder](http://www.scons.org/wiki/MexBuilder).  The difference to
this tool is mainly that it executes the mex program, while the `Mex()`
pseudo-builder in this tool wraps the `SharedLibrary()` builder.

License
-------

See the file LICENSE.
