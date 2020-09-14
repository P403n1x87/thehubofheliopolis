Title:    Extending Python with Assembly
Authors:  Gabriele N. Tornetta
Date:     2018-03-24 00:32:00 +0100
Github:   P403n1x87/asm/tree/master/python
Category: Programming
Tags:     python, assembly
pic:      asm_python
Summary:  What's a better way to fill an empty evening if not by reading about how to extend Python with Assembly? I bet you don't even know where to start to answer this question :P. But if you're curious to know how you can use another language to extend Python, and if you happen to like Assembly programming, you might end up actually enjoying this post (I hope!).


[TOC]


# Introduction

If you have landed on this page, you must have had one between two only possible
reactions to the title of this post, either "Hmm, this sounds interesting" or
"Just, why?". The straight answer is, well, "just, because". And perhaps a bit
more articulated answer is: because the people in the first category probably
enjoy this kind of things :).

Reactions aside, the subject of this post is the coding of an extension for
Python written in pure Assembly for the Intel x86-64 architecture on a
Linux-based operating system. If you are familiar with general assembly but have
never coded for the architecture that we are targeting, it is perhaps worth
reading through my previous post "[Getting Started with x86-64 Assembly on
Linux]({filename}2016-08-10-getting-started-with-x64-asm.md)".

I will also assume that you are somewhat familiar with extending Python with C.
If not, then it probably is a good idea to go through the [official
documentation](https://docs.python.org/3/extending/extending.html) before
reading on, or some things might not make too much sense. The approach of this
post is by example and builds on knowledge about C to transition to Assembly. My
favourite assembler on Linux is NASM, since it supports the Intel syntax, the
one that I am more comfortable with. Therefore the only dependencies for
following along are the NASM assembler and the GNU linker `ld`. Optionally, we
can make use of a `Makefile` to assemble and link our code, and perhaps `docker`
to test it in a clean environment. You will find all the relevant files in the
linked [GitHub repository](https://github.com/P403n1x87/asm/tree/master/python).

Now it's time to jump straight into the code.

# The Code

There isn't much more to say before we can see the code really, so here it is.
This is the content of my `asm.asm` source file.

	#!nasm
	DEFAULT                 rel

	%include                "asm/python.inc"

	GLOBAL                  PyInit_asm:function


	;; ---------------------------------------------------------------------------
	SECTION                 .rodata
	;; ---------------------------------------------------------------------------

	l_sayit_name            db "sayit", 0
	l_sayit_doc             db "This method has something important to say.", 0
	l_sayit_msg             db "Assembly is great fun! :)", 10
	l_sayit_msg_len         equ $ - l_sayit_msg

	l_module_name           db "asm", 0


	;; ---------------------------------------------------------------------------
	SECTION                 .data
	;; ---------------------------------------------------------------------------

	l_asm_methods:              ;; struct PyMethodDef[] *
	ISTRUC PyMethodDef
	  at PyMethodDef.ml_name    , dq l_sayit_name
	  at PyMethodDef.ml_meth    , dq asm_sayit
	  at PyMethodDef.ml_flags   , dq METH_NOARGS
	  at PyMethodDef.ml_doc     , dq l_sayit_doc
	IEND
	NullMethodDef

	l_asm_module:                ;; struct PyModuleDef *
	ISTRUC PyModuleDef
	  at PyModuleDef.m_base     , PyModuleDef_HEAD_INIT
	  at PyModuleDef.m_name     , dq l_module_name
	  at PyModuleDef.m_doc      , dq NULL
	  at PyModuleDef.m_size     , dq -1
	  at PyModuleDef.m_methods  , dq l_asm_methods
	  at PyModuleDef.m_slots    , dq NULL
	  at PyModuleDef.m_traverse , dq NULL
	  at PyModuleDef.m_clear    , dq 0
	  at PyModuleDef.m_free     , dq NULL
	IEND


	;; ---------------------------------------------------------------------------
	SECTION                 .text
	;; ---------------------------------------------------------------------------

	asm_sayit: ;; ----------------------------------------------------------------
	                        push  rbp
	                        mov   rbp, rsp

	                        mov   rax, 1                  ; SYS_WRITE
	                        mov   rdi, 1                  ; STDOUT
	                        mov   rsi, l_sayit_msg
	                        mov   rdx, l_sayit_msg_len
	                        syscall

	                        mov   rax, Py_None
	                        inc   QWORD [rax + PyObject.ob_refcnt]

	                        pop   rbp
	                        ret
	;; end asm_sayit


	PyInit_asm: ;; --------------------------------------------------------------
	                        push  rbp
	                        mov   rbp, rsp

	                        mov   rsi, PYTHON_API_VERSION
	                        mov   rdi, l_asm_module
	                        call  PyModule_Create2 WRT ..plt

	                        pop   rbp
	                        ret
	;; end PyInit_asm


If you have never written a C extension for Python before, this might look a bit
mysterious to you, although the general structure, at least, should be quite
clear after you've glimpsed through the official Python documentation on
extending Python with C.

We shall now analyse every single part of the above code sample in details to
see what each block of code does.

## Shared Object

On the very first line of the source we see the line

	:::nasm
	DEFAULT                 rel


Our goal is to assemble and link our code into an ELF64 _shared object_ file.
Contrary to ordinary program code, shared object files are dynamically loaded
into random memory addresses. It is therefore important that all our code is
_position-independent_. One way of doing this is to make sure that any memory
reference is not absolute, but relative to the value of the `RIP` register,
which points to the current instruction being executed. This guarantees that, no
matter where the shared object is loaded into memory, references to local
variables are correct. In 64-bit mode, NASM defaults to absolute addresses,
therefore the above line is necessary to switch to `RIP`-relative addresses.

## The CPython Headers

On line 3 we include a file to our main Assembly source. Given the simplicity of
this example, we could have included the content of the `python.inc` file within
`asm.asm` itself. However, for larger projects it is perhaps good practice to
separate declarations and actual code, like it is usually done in C, with `.h`
and `.c` files. In fact, the `python.inc` file includes the equivalent of
structures and macros as declared in the CPython header files. As far as I'm
aware, there are no assembly-specific include files provided by the maintainers
of CPython, so we have to go through the extra effort of typing them ourselves.
We will get back to the content of this file later on.

## Exporting Global Symbols

Line 5 is an important one. It exports the symbol `PyInit_asm`, of type
`function`, and makes it available for external programs. This is the function
that CPython calls the moment we load the `asm` module with `import asm` from
the Python interpreter. If we do not export this symbol, then CPython won't be
able to find the code necessary to initialise the module. In analogy with C,
this is equivalent to declaring a non-static function.

## Immutable Strings

Next we have the read-only data section

	:::nasm
	;; ---------------------------------------------------------------------------
	SECTION                 .rodata
	;; ---------------------------------------------------------------------------

	l_sayit_name            db "sayit", 0
	l_sayit_doc             db "This method has something important to say.", 0
	l_sayit_msg             db "Assembly is great fun! :)", 10
	l_sayit_msg_len         equ $ - l_sayit_msg

	l_module_name           db "asm", 0


Here we initialise the strings that we will need later on. As they won't change
during the course of the code execution, we put them in a read-only section of
the shared object. The GNU C compiler does just the same thing with every
literal string that you use in C code. You will notice references to their
address in the following section, that of (read-write) initialised data.

## CPython Data Structures

Next is the section of initialised data.

	:::nasm
	;; ---------------------------------------------------------------------------
	SECTION                 .data
	;; ---------------------------------------------------------------------------

	l_asm_methods:              ;; struct PyMethodDef[] *
	ISTRUC PyMethodDef
	  at PyMethodDef.ml_name    , dq l_sayit_name
	  at PyMethodDef.ml_meth    , dq asm_sayit
	  at PyMethodDef.ml_flags   , dq METH_NOARGS
	  at PyMethodDef.ml_doc     , dq l_sayit_doc
	IEND
	NullMethodDef

	l_asm_module:               ;; struct PyModuleDef *
	ISTRUC PyModuleDef
	  at PyModuleDef.m_base     , PyModuleDef_HEAD_INIT
	  at PyModuleDef.m_name     , dq l_module_name
	  at PyModuleDef.m_doc      , dq NULL
	  at PyModuleDef.m_size     , dq -1
	  at PyModuleDef.m_methods  , dq l_asm_methods
	  at PyModuleDef.m_slots    , dq NULL
	  at PyModuleDef.m_traverse , dq NULL
	  at PyModuleDef.m_clear    , dq 0
	  at PyModuleDef.m_free     , dq NULL
	IEND


Here is where things start to get interesting, and the content of the
`python.inc` file comes into play. The first two labels point to the beginning
of CPython-specific structures. The first is an array of `PyMethodDef`
structures. As the name suggests, each instance of this structure is used to
hold information about a method that should be made available to the Python
interpreter from within our module. To find out in which header file it is
defined, we can use the command

	:::shell
	grep -nr /usr/include/python3.6 -e "struct PyMethodDef"


In my case, I get that the structure is defined in
`/usr/include/python3.6/methodobject.h`, starting from line 54. Inside the
`python.inc` we then have the equivalent structure declaration

	:::nasm
	STRUC PyMethodDef
	  .ml_name              resq 1    ; const char *
	  .ml_meth              resq 1    ; PyCFunction
	  .ml_flags             resq 1    ; int
	  .ml_doc               resq 1    ; const char *
	ENDSTRUC


The `NullMethodDef` is a NASM macro that conveniently defines the _sentinel_
`PyMethodDef` structure, which is used to mark the end of the `PyMethodDef`
array pointed by `l_asm_methods`. Its definition is also in the `python.inc`
file and, as you can see, simply initialises a new instance of the structure
with all the fields set to `NULL` or 0, depending on their semantics, i.e.
whether they are memory pointers or general integers.

	:::nasm
	%define NullMethodDef         dq NULL, NULL, 0, NULL


> Note that `NULL` is not a native NASM value. To align the coding conventions
> with C, I have defined NULL as a constant in `python.inc` and assigned the
> value of 0 to it. The idea is that, like in C, it makes the intent of the code
> clearer, since any occurrence of `NULL` indicates a null pointer rather than
> just the literal value 0.

The next label, `l_asm_module`, points to an instance of the `PyModuleDef`
structure, which is pretty much the core data structure of our Python module. It
contains all the relevant metadata that is then passed to CPython for correct
initialisation and use of the module. Its definition is in the `moduleobject.h`
header file and, at first sight, looks a bit complicated, with some references
to other structures and C macros.

	:::C
	typedef struct PyModuleDef{
	  PyModuleDef_Base m_base;
	  const char* m_name;
	  const char* m_doc;
	  Py_ssize_t m_size;
	  PyMethodDef *m_methods;
	  struct PyModuleDef_Slot* m_slots;
	  traverseproc m_traverse;
	  inquiry m_clear;
	  freefunc m_free;
	} PyModuleDef;


So lets take our time to figure out what its byte content looks like. The first
field is an instance of the `PyModuleDef_Base` structure, which is defined in
the same header file, just a few lines above. The non-trivial bit in this new
structure is the first part, `PyObject_HEAD`, which looks like a C macro. As the
name suggest, its definition is quite likely to be found in `object.h`. Indeed,
there we find

	:::C
	#define PyObject_HEAD                   PyObject ob_base;

so our chase continues. The definition of the `PyObject` structure can be found
a few lines below. Again, all the fields are quite simple, i.e. just integers
value or memory pointers, except for the macro `_PyObject_HEAD_EXTRA`. We then
have to jump back up a few lines, to find that this macro is conditionally
defined as either nothing or `0, 0`. By default, the macro `Py_TRACE_REFS` is
not defined, so in our case `_PyObject_HEAD_EXTRA` evaluates to nothing.
Backtracking from our macro chase in CPython headers, we see that we can define
the following structures in `python.inc`

	:::nasm
	STRUC PyObject
	  .ob_refcnt            resq 1    ; Py_ssize_t
	  .ob_type              resq 1    ; struct _typeobject *
	ENDSTRUC

	STRUC PyModuleDef_Base
	  .ob_base              resb PyObject_size
	  .m_init               resq 1    ; PyObject *
	  .m_index              resq 1    ; Py_ssize_t
	  .m_copy               resq 1    ; PyObject *
	ENDSTRUC

	STRUC PyModuleDef
	  .m_base               resb PyModuleDef_Base_size
	  .m_name               resq 1    ; const char *
	  .m_doc                resq 1    ; const char *
	  .m_size               resq 1    ; Py_ssize_t
	  .m_methods            resq 1    ; PyMethodDef *
	  .m_slots              resq 1    ; struct PyModuleDef_Slot *
	  .m_traverse           resq 1    ; traverseproc
	  .m_clear              resq 1    ; inquiry
	  .m_free               resq 1    ; freefunc
	ENDSTRUC


As you can easily guess, NASM generates the constants `PyObject_size` etc...
automatically so that they can be used to reserve enough memory to hold the
entire structure in the definition of other structures. This makes nesting quite
easy to implement in NASM.

## Local and Global Functions

Finally we get to the actual code that will get executed by CPython when our
module is loaded and initialised, and when the methods that it provides are
called.

	:::nasm
	;; ---------------------------------------------------------------------------
	SECTION                 .text
	;; ---------------------------------------------------------------------------

	asm_sayit: ;; ----------------------------------------------------------------
	                        push  rbp
	                        mov   rbp, rsp

	                        mov   rax, 1                  ; SYS_WRITE
	                        mov   rdi, 1                  ; STDOUT
	                        mov   rsi, l_sayit_msg
	                        mov   rdx, l_sayit_msg_len
	                        syscall

	                        mov   rax, Py_None
	                        inc   QWORD [rax + PyObject.ob_refcnt]

	                        pop   rbp
	                        ret
	;; end asm_sayit


	PyInit_asm: ;; --------------------------------------------------------------
	                        push  rbp
	                        mov   rbp, rsp

	                        mov   rsi, PYTHON_API_VERSION
	                        mov   rdi, l_asm_module
	                        call  PyModule_Create2 WRT ..plt

	                        pop   rbp
	                        ret
	;; end PyInit_asm


In fact, we have a total of two functions, one local and one global. The first
one, `asm_sayit`, is the only method contained in our module. All it does is to
write a string, `l_sayit_msg`, to standard output by invoking the `SYS_WRITE`
system call. Perhaps the most interesting bit of this function is the code on
lines 61-62. This is the idiom for any function that wishes to return `None` in
Python. Recall that, in Python, `None` is an object instantiated by CPython. As
such, our shared library needs to import it as an external symbol. This is why
you will find the macro `PyNone` defined as

	:::nasm
	%define Py_None               _Py_NoneStruct


together with the line

	:::nasm
	EXTERN    _Py_NoneStruct


in the `python.inc` file. This is equivalent to the two lines

	:::C
	PyAPI_DATA(PyObject) _Py_NoneStruct; /* Don't use this directly */
	#define Py_None (&_Py_NoneStruct)


in the `object.h` header file, where the `None` object is defined. All of this
explains line 61, but what about line 62? This has to do with [Reference
Counting](https://docs.python.org/3/c-api/refcounting.html). In a nutshell,
every object created in Python comes with a counter that keeps track of all the
references attached to it. When the counter gets down to 0, the object can be
de-allocated from memory and resources freed for other objects to use. This is
how Python, which heavily relies on `malloc`, can keep memory leaks at bait. It
is therefore very important to properly maintain reference counts in Python
extensions. As `None` is a Python object like any others, when we return a
reference to it, we have to bump its reference count. In C, this is conveniently
done with the `Py_INCREF` macro. Its definition is in the `object.h` and, as it
is easy to guess, it just increases the `ob_refcnt` field of the `PyObject`
structure. This is precisely what we do on line 62.

> **Stack Frames Matter!** You might be wondering why we are taking care of
> creating a stack frame on function entry, and cleaning up after ourself on
> leave. The reason is a pretty obvious one: we don't know what code will call
> ours, so it is safe to make sure that stack alignment is preserved across
> calls by doing what every function is expected to do. When I was lying down
> the code for this post, I was getting a SIGSEGV exception, and the debugger
> revealed that the instruction `movaps` was trying to store the value of the
> `xmm0` register on a memory location that was not a multiple of 16. The
> problem was solved by the extra 8 bytes from `push rbp`.

The second and last function is our global exported symbol `PyInit_asm`. It gets
called by CPython as soon as we `import` the module with `import asm`. In this
simple case, we don't have to do much here. In fact, all we have to do is call a
standard CPython function and pass it the instance of `PyModuleDef` allocated at
`l_asm_module`. As we have briefly seen, this contains all the information about
our module, from the documentation to the list of methods.

Now, if you have read through the official documentation on how to extend Python
with C, you might be wondering why we are calling `PyModule_Create2` instead of
`PyModule_Create` (is there a typo?), and why we are passing it two arguments
instead of one. If you are starting to smell a C macro, then you are correct!
Long story short, `PyModule_Create` is a macro defined as

	:::C
	#define PyModule_Create(module) PyModule_Create2(module, PYTHON_API_VERSION)


with `PYTHON_API_VERSION` defined as the literal 1013. So the actual function to
call is indeed `PyModule_Create2`, and it takes two arguments.

> Did you notice that weird `WRT ..plt`? Remember the discussion about ensuring
> position-independent code? Since we have no clue of where the
> `PyModule_Create2` function resides in memory, we have to rely on some sort of
> indirection. This is provided by the so-called _Procedure Linkage Table_, or
> _PLT_ for short, which is some code that is part of our shared library. When
> we call `PyModule_Create2 WRT ..plt`, we are jumping to the PLT section of our
> object file in memory, which contains the necessary code to make the actual
> jump to the function that we want to call.


# Installation

Once our assembly code is ready, it needs to be assembled and linked into a
shared object file. We will now see how to perform these steps, and how to test
and install our Python extension.

## Assembling and Linking

Once the code is ready, it needs to be assembled and linked into the final
shared object file. The NASM assembler is invoked with minimal arguments as

	:::shell
	nasm -f elf64 -o asm/asm.o asm/asm.asm


This creates an intermediate object file `asm.o`. To create the final shared
object file, we use the GNU linker with the following arguments

	:::shell
	ld -shared -o asm/asm.so asm/asm.o -I/lib64/ld-linux-x86-64.so.2


Note the use of the `-shared` switch, which instructs the linker to create a
shared object file.


## How to Test the Module

The first thing that you might want to do is to manually test that the shared
object file works fine with Python. For CPython to be able to find the module,
we need to ensure that its location is included in the search path. One way is
to add it to the `PYTHONPATH` environment variable. For example, from within the
project folder, we can launch Python with

	:::shell
	PYTHONPATH=./asm python3


and from the interactive session we should be able to import the module with

	:::python
	>>> import asm
	>>>


Alternatively, we can add the search path to `sys.path` with these few lines of
Python code

	:::python
	>>> import sys
	>>> sys.path.append("./asm")
	>>> import asm
	>>>


Once we have successfully imported our module in Python, we can test that its
method `sayit` works as expected

	:::python
	>>> asm.sayit.__doc__
	'This method has something important to say.'
	>>> asm.sayit()
	Assembly is great fun! :)
	>>>


I hope that you would agree :).


## Distributing the Module

The simplicity of our sample module wouldn't justify the use of `setuptools` for
distribution. In this case, a simple, old-fashioned Makefile is the simplest
solution to go for. Even for larger projects, you would probably still delegate
the build job of your code to a Makefile anyway, which would then get called
from your `setup.py` at some phase, perhaps during `build`. However, the
recommended standard is that you build _wheels_ instead of _eggs_, and the
requirement is that you provide pre-built binaries with your package.

This being said, let's see how to distribute the module. As we have seen in the
previous section, the shared object needs to resides in one of the Python search
paths. The easiest way to find out what these paths are on the platform that you
are targeting is to launch the Python interpreter and print the value of
`sys.path`. On my platform, I get the following output

	:::python
	Python 3.6.3 (default, Oct  3 2017, 21:45:48)
	[GCC 7.2.0] on linux
	Type "help", "copyright", "credits" or "license" for more information.
	>>> import sys
	>>> sys.path
	['', '/usr/lib/python36.zip', '/usr/lib/python3.6', '/usr/lib/python3.6/lib-dynload', '/usr/local/lib/python3.6/dist-packages', '/usr/lib/python3/dist-packages', '/usr/lib/python3.6/dist-packages']
	>>>


The Makefile could then contain the following line inside the `install` rule:

	:::bash
	install: default
		cp asm/asm.so /usr/lib/python${PYTHON_TARGET}/asm.so


with the environment variable `PYTHON_TARGET` set to `3.6`.

To automate the building and testing process of the module, we could use Docker
to build an image out of the target platform and trigger a build, and perhaps
execute some unit tests too. A simple Dockerfile that does the minimum work to
build and test would look something like the following

	:::dockerfile
	FROM  ubuntu:latest
	USER  root
	ADD   . asm
	RUN   apt-get update              &&\
	      apt-get install -y            \
	        nasm                        \
	        python3-pytest              \
	        build-essential
	ENV   PYTHON_TARGET=3.5
	RUN   cd asm                      &&\
	      make                        &&\
	      make install                &&\
	      python3 -m pytest -s


As you can see, we are targeting the latest stable version of Ubuntu, which
comes with `python3.5`. We make sure we install all the required dependencies,
the assembler and the standard build tools, along with `python3-pytest` to
perform unit testing once our module builds successfully.

The bare minimum that we can test is that the import of the module works fine
and that we can call its method. So a possible `test_asm.py` test script would
look like

	:::python
	import asm


	def test_asm():
	    asm.sayit()


# Conclusions

Whilst I appreciate that the cases where you'd want to seriously consider
extending Python with Assembly code are rare, it is undoubtedly the case that,
if you enjoy experimenting with code, this could be a fun and instructing
experience. In my case, this has forced me to go look into the CPython header
files, which I probably wouldn't have if I were using C. I now know more about
the internal workings of Python and a clearer idea of how CPython is structured.

As always, I hope you have enjoyed the read. Happy Assembly coding! :)
