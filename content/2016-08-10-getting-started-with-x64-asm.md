Title:    Getting Started with x86-64 Assembly on Linux
Authors:  Gabriele N. Tornetta
Date:     2016-08-10 15:48:37 +0100
Category: Programming
Tags:     assembly
pic:      intro-asm-x64
art:      asm-header.png
Summary:  You have experience of x86 assembly and you wonder what the fundamental architectural differences with the 64 bit Intel architecture are? Then this post might be what you are looking for. Here we'll see how to use the Netwide Assembler (NASM) to write a simple Hello World application in x86_64 assembly. Along the way, we will also have the chance to see how to use some standard tools to optimise the final executable by stripping out unnecessary debug symbols.

[TOC]

In this post we will learn how to assemble and link a simple "Hello World"
application written in x86-64 assembly for the Linux operating system. If you
have experience with Intel IA-32 assembly and you want to quickly get adjusted
to the x86-64 world then this post is for you. If you're trying to learn the
assembly language from scratch then I'm afraid this post is not for you. There
are many great resources online on 32-bit assembly. One of my favourite
documents is Paul Carter's PC Assembly Language, which I highly recommend if
you're moving your first steps into the assembly language. If you then decide to
come back to this post, you should be able to read it with no problems, since
the tools that I will employ here are the same used in Carter's book.

# Overview

This post is organised as follows. In the next section, I gather some details
about the tools that we will use to code, assemble, link and execute the
applications. As already mentioned above, most of the tools are the same as
those used in Carter's book. Our assembler (and hence the syntax) will be NASM.
I will make use of two linkers, `ld` and the one that comes with `gcc`, the GNU
C Compiler, for reasons that will be explained later. The first x64 application
that we will code will give us the chance to get familiar with the new system
calls and how they differ from the 32-bit architecture. With the second one we
will make use of the Standard C Library. Both examples will give us the chance
to explore the x86-64 calling convention as set out in the [System V Application
Binary Interface](http://www.x86-64.org/documentation/abi.pdf).

All the code shown in this post will also be available from the [dedicated asm
GitHub repository](https://github.com/P403n1x87/asm/tree/master/hello64).

# Tools

The Netwide Assembler is arguably the most popular assembler for the Linux
Operating System and it is an open-source project. Its documentation is nicely
written and explains all the features of the language and of the (dis)assembler.
This post will try to be as much self-contained as possible, but whenever you
feel the need to explore something a bit more, the NASM documentation will
probably be the right place. To assemble a 64-bit application we will need to
use the command

	:::shell
	nasm -f elf64 -o myapp.o myapp.asm


The flag `-f elf64` instructs NASM that we want to create a 64-bit ELF object
file. The flag `-o myapp.o` tells the assembler that we want the output object
file to be `myapp.o` in the current directory, whereas `myapp.asm` specifies the
name of the source file containing the NASM code to be assembled.

When an application calls functions from shared libraries it is necessary to
_link_ our object file to them so that it knows where to find them. Even if we
are not using any external libraries, we still need to invoke the linker in
order to obtain a valid executable file. The typical usage of `ld` that we will
encounter in this post is

	:::shell
	ld -o myapp.o myapp


This is enough to produce a valid executable when we are not linking our object
file `myapp.o` against any external shared library or any other object file.
Occasionally, depending on your distribution, you will have to specify which
interpreter you want to use. This is a library which, for ELF executables, acts
as a loader. It loads the application in memory, as well as the required linked
shared libraries. On Ubuntu 16.04, the right 64-bit interpreter is at
`/lib64/ld-linux-x86-64.so.2` and therefore my invocation of `ld` will look like

	:::shell
	ld -o myapp myapp.o -I/lib64/ld-linux-x86-64.so.2


Some external shared libraries are designed to work with C. It is then advisable
to include a `main` function in the assembly source code since the Standard C
Library will take care of some essential cleanup steps when the execution
returns from it. Cases where one might want to opt for this approach are when
the application works with file descriptors and/or spawns child processes. We
will see an example of this situation in a future tutorial on assembly and Gtk+.
For the time being, we shall limit ourselves to see how to use the GNU C
Compiler to link our object file with other object files (and in particular with
`libc`). The typical usage of `gcc` will be something like

	:::shell
	gcc -o myapp.o myapp


which is very much similar to `ld`.

# Hello Syscalls!

In this first example we will make use of the Linux system calls to print the
string `Hello World!` to the screen. Here is where we encounter a major
difference between the 32-bit and the 64-bit Linux world.

But before we get to that, let's have a look at what is probably the most
important difference between the 32-bit and the 64-bit architecture: the
registers. The number of the general purpose registers (GPRs for short) has
doubled and now have a maximum size of ... well ... 64-bit. The old `EAX`,
`EBX`, `ECX` etc... are now the low 32-bit of the larger `RAX`, `RBX`, `RCX`
etc... respectively, while the new 8 GPRs are named `R8` to `R15`. The prefix
`R` stands for, surprise, surprise, _register_. This seems like a sensible
decision, since this is in line with many other CPU manufacturers. Further
details can be found in [Chapter 11](http://www.nasm.us/doc/nasmdo11.html) of
the NASM documentation and in [this Intel
white](https://software.intel.com/sites/default/files/m/d/4/1/d/8/Introduction_to_x64_Assembly.pdf).

Let's now move back to system calls. Unix systems and derivatives do not make
use of software interrupts, with the only exception of `INT 0x80`, which on
32-bit systems is used to make system calls. A system call is a way to request a
service from the kernel of the operating system. Most C programmers don't need
to worry about them, as the Standard C Library provides wrappers around them.
The x86_64 architecture introduced the dedicated instruction `syscall` in order
to make system calls. You can still use interrupts to make system calls, but
`syscall` will be faster as it does not access the interrupt descriptor table.

The purpose of this section is to explore this new opcode with an example.
Without further ado, let's dive into some assembly code. The following is the
content of my `hello64.asm` file.

	#!nasm
	global _start

	;
	; CONSTANTS
	;
	SYS_WRITE   equ 1
	SYS_EXIT    equ 60
	STDOUT      equ 1

	;
	; Initialised data goes here
	;
	SECTION .data
	hello           db  "Hello World!", 10      ; char *
	hello_len       equ $-hello                 ; size_t

	;
	; Code goes here
	;
	SECTION .text

	_start:
	    ; syscall(SYS_WRITE, STDOUT, hello, hello_len);
	    mov     rax, SYS_WRITE
	    mov     rdi, STDOUT
	    mov     rsi, hello
	    mov     rdx, hello_len
	    syscall
	    push    rax

	    ; syscall(SYS_EXIT, <sys_write return value> - hello_len);
	    mov     rax, SYS_EXIT
	    pop     rdi
	    sub     rdi, hello_len
	    syscall
*hello64.asm*

Lines 1, 13, 20 and 22 are part of the skeleton of any NASM source code. With
line 1 we export the symbol `_start`, which defines the entry point for the
application, i.e. the point in where the execution starts from. The actual
symbol is declared on line 22, and line 24 will be the fist one to be executed.

In lines 6 to 8 we define some constants to increase the readability of the
code. The price to pay is that NASM will export these symbols as well, thus
increasing the size of the final executable file. I will discuss how to deal
with this later on in this post. For the time being, let's focus on the rest of
the code.

Line 13 marks the beginning of the initialised data section. Here we define
strings and other immediate values. In this case we only need to define the
`"Hello World!\n"` string (`10` is the ASCII code for the newline character
`\n`) and label it `hello`. Line 15 defines a constant equals to the length of
the string, and this is accomplished by subtracting the address of the label
`hello` from the current address, given by `$` in NASM syntax.

The `.text` section, where the actual code resides, starts at line 20\. Here we
declare the `_start` symbol, i.e. the entry point of the application, followed
by the code to be executed. In this simple example, all we need to do is print
the string to screen and then terminate the application. This means that we need
to call the `sys_write` system call, followed by a call to `sys_exit`, perhaps
with an exit code that will tell us whether the call to `sys_write` has been
successful or not.

Here is our first encounter with the new syscall opcode and the x86_64 calling
convention. There isn't much to say about syscall. It does what you would expect
it to do, i.e. make a system call. The system call to make is specified by the
value of the rax register, whereas the parameters are passed according to the
already mentioned x86_64 calling convention. It is recommended that you have a
look at the official documentation to fully grasp it, especially when it comes
to complex calls. In a nutshell, some of the parameters are passed through
registers and the rest go to the stack.

> The order of the registers is: `rdi`, `rsi`, `rdx`, `r10`, `r8`, `r9`.

We shall see in the next code example that, when we call a C function, we should
use `rcx` instead of `r10`. Indeed, the latter is only used for the Linux kernel
interface, while the former is used in all the other cases.

On line 23 we have a comment that shows us the equivalent C code for a call to
`sys_write`. Its "signature" is the following.

	:::text
	1. SYS_WRITE

	Parameters
	----------

	unsigned int	file descriptor
	const char *	pointer to the string
	size_t	 			number of bytes to write


	Return value
	------------
	The number of bytes of the pointed string written on the file descriptor.

The number that appears on the top right corner is the code associated to the
system call (compare this with line 6 above), and by convention this goes into
the `rax` register (see line 24). Since `sys_write` requires 3 integer
parameters we only need the registers `rdi`, `rsi` and `rdx`, in this order.
Therefore, the file descriptor, the standard output in this case, will go in
`rdi`, the address of the first byte of the string will go in `rsi` while its
length will be loaded into `rdx` (lines 25 to 27).

In order to make the actual system call we can now use the new opcode `syscall`.
The return value, namely the number of bytes written by `sys_write` in this
case, is returned in the `rax` register. With line 29 we save the return value
in the stack in order to use it as an exit code to be passed to `sys_exit`.

Since the application has done everything that needed to be done, i.e. print a
string to standard output, we are ready to terminate the execution of the main
process. This is achieved by making the exit system call, whose "signature" is
the following.

	:::text
	60. SYS_EXIT

	Parameters
	----------

	int		error code


	Return value
	------------
	This system call does not return.

With line 32 we load the code of `sys_exit` into the `rax` register in
preparation for the system call. As error code, we might want to return `0` if
`sys_write` has done its job properly, i.e. if it has written all the expected
number of bytes, and something else otherwise. The simplest way to achieve this
is by subtracting the string length from the return value of `sys_write`.
Remember that we stored the latter in the stack, so it is now time to retrieve
it. The first and only argument of `sys_exit` must go in `rdi`, so we might as
well pop the `sys_write` return value in there directly, and this is precisely
what line 33 does. On line 34 we subtract the length of the string from `rdi`,
so that if `sys_write` has written all the expected number of bytes, `rdi` will
now be `0`. The last instruction on line 35 is the `syscall` opcode that will
make the system call and terminate the execution.

All right, time now to assemble, link and execute the above code.

	:::shell
	nasm -f elf64 -o hello64.o hello64.asm
	ld -o hello64 hello64.o -I/lib64/ld-linux-x86-64.so.2


This will assemble the source code of `hello64.asm` into the object file
`hello64.o`, while the linker will finish off the job by linking the interpreter
to the object file and produce the ELF64 executable. To run the application,
simply type

	:::shell
	./hello64


If you also want to display the exit code to make sure the executable is
behaving as expected we could use

	:::shell
	./hello64; echo "exit code:" $?


and, on screen, we should now see

	:::text
	Hello World!
	exit code: 0


Apart from the fun, another reason to write assembly code is that you can shrink
the size of the executable file. Let's check how big `hello64` is at this stage

	:::text
	$ wc -c < hello64
	1048


A kilobyte seems a bit excessive for an assembly application that only prints a
short string on screen. The reason of such a bloated executable is in the symbol
table created by NASM. This plays an important role inside our ELF file in case
we'd need to link it with other object files. You can see all the symbols stored
in the elf file with

	:::text
	$ objdump -t hello64

	hello64:     file format elf64-x86-64

	SYMBOL TABLE:
	00000000004000b0 l    d  .text 0000000000000000 .text
	00000000006000d8 l    d  .data 0000000000000000 .data
	0000000000000000 l    df *ABS* 0000000000000000 hello64.asm
	0000000000000001 l       *ABS* 0000000000000000 SYS_WRITE
	000000000000003c l       *ABS* 0000000000000000 SYS_EXIT
	0000000000000001 l       *ABS* 0000000000000000 STDOUT
	00000000006000d8 l       .data 0000000000000000 hello
	000000000000000d l       *ABS* 0000000000000000 hello_len
	00000000004000b0 g       .text 0000000000000000 _start
	00000000006000e5 g       .data 0000000000000000 __bss_start
	00000000006000e5 g       .data 0000000000000000 _edata
	00000000006000e8 g       .data 0000000000000000 _end


Assuming that we are not planning of doing this with our simple Hello World
example, we strip the symbol table off `hello64` with

	:::shell
	strip -s hello64


If we now check the file size again, this is what we get

	:::text
	$ wc -c < hello64
	512


i.e. less than half the original size. Looking at the symbol table again, this
is what we get now:

	:::text
	$ objdump -t hello64

	hello64: file format elf64-x86-64

	SYMBOL TABLE:
	no symbols


Observe that we can obtain the same result with the -s switch to the linker we
decide to use, that is, either ld or gcc. Thus, for example,

	:::shell
	ld -s -o hello64 hello64.o


will produce an ELF executable that lacks the symbol table completely.

The possibility of removing symbols from an ELF file gives us the chance of
defining the constants for the system calls once and for all. In my GitHub
repository you can find the file
[`syscalls.inc`](https://github.com/P403n1x87/asm/blob/master/syscalls/syscalls.inc)
where I have defined all the system calls together with their associated ID, and
the "signature" of each on a comment line. With the help of this file, our
source code would look like this

	#!nasm
	global _start

	%include "../syscalls.inc"

	;
	; CONSTANTS
	;
	STDOUT      equ 1

	;
	; Initialised data goes here
	;
	SECTION .data
	hello           db  "Hello World!", 10      ; char *
	hello_len       equ $-hello                 ; size_t

	;
	; Code goes here
	;
	SECTION .text

	_start:
	    ; syscall(SYS_WRITE, STDOUT, hello, hello_len);
	    mov     rax, SYS_WRITE
	    mov     rdi, STDOUT
	    lea     rsi, [hello]
	    mov     rdx, hello_len
	    syscall
	    push    rax

	    ; syscall(SYS_EXIT, <sys_write return value> - hello_len);
	    mov     rax, SYS_EXIT
	    pop     rdi
	    sub     rdi, hello_len
	    syscall
*hello64_inc.asm*

Note the inclusion of the file `syscalls.inc` at line 3, assumed to be stored in
the parent folder of the one containing the assembly source code, and the only
constant `STDOUT` at line 8.

If you do not need symbols in the final ELF file, you can just remove the symbol
table completely with the previous command. However, if you want to retain some,
but get rid of the one associated to constants that are meaningful to just your
source code, you can add a `-N <symbol name>` (e.g. `strip -N STDOUT hello64`)
switch to strip for each symbol you want dropped. To automate this when using
`syscalls.inc`, one can execute the following (rather long) command

	:::shell
	strip `while IFS='' read -r line || [[ -n "$line" ]]; do read s _ <<< $line; echo -n "-N $s "; done < <(tail -n +5 ../syscalls.inc)` hello64


on the ELF executable.

Finally, let's verify that all we really have is pure assembly code, i.e. that
our application doesn't depend on external shared objects:

	:::text
	$ ldd hello64
	        not a dynamic executable


In this case, this output is telling us that `hello64` is not linked to any
other shared object files.

# Hello libc!

We shall now rewrite the above Hello World! example and let the Standard C
Library take care of the output operation. That is, we won't deal with system
calls directly, we shall instead delegate a higher abstraction layer, the
Standard C Library, do that for us. Furthermore, with this approach, we will
also delegate some basic clean-up involving, e.g., open file descriptor, child
processes etc..., which we would have to deal with otherwise. For a simple
application like a Hello World! this last point is pretty much immaterial, but
we will see in another post on GUIs with Gtk+ 3 the importance of waiting for
child processes to terminate an application gracefully.

So the code we want to write is the assembly analogue of the following C code

	:::C
	#include <stdio.h>

	int main()
	{
	  return printf("Hello World!\n") - 13;
	}


Inside the `main` function, we call `printf` to print the string on screen and
then use its return value, decreased by the string length, as exit code. Thus,
if `printf` writes all the bytes of our string, we get 0 as exit code, meaning
that the call has been successful.

The didactic importance of this example resides in the use of the variadic
function `printf`. The System V ABI specifies that, when calling a variadic
function, the register `rax` should hold the number of XMM registers used for
parameter passing. In this case, since we are just printing a string, we are not
passing any other arguments apart from the location of the first character of
the string, and therefore we need to set `rax` to zero. With all these
considerations, the assembly analogue of the above C code will look like this

	#!nasm
	global main

	extern printf

	;
	; Initialised data goes here
	;
	SECTION .data
	hello           db  "Hello World!", 10, 0   ; const char *
	hello_len       equ $ - hello               ; size_t
	;
	; Code goes here
	;
	SECTION .text

	; int main ()
	main:
	    ; return printf(hello) - hello_len;
	    lea     rdi, [hello]
	    xor     rax, rax
	    call    printf
	    sub     rax, hello_len
*hello64_libc.asm*

On line 1 we export the main symbol, which will get called by the `libc`
framework. On line 3 we instruct NASM that our application uses an external
symbol, i.e. the variadic function `printf`. There is nothing new to say about
the `.data` section, that starts at line 8\. The code, however, is quite
different. On line 17 we declare the label `main`, which marks the entry point
of the C main function. We do not need local variables no access the standard
argument of `main`, namely `argc` and `argv`, so we do not create a local stack
frame. Instead, we go straight to calling `printf`. We load the string address
in the `rdi` register (line 19), set the `rax` register to zero (line 20), since
we are not passing any arguments by the XMM registers, and finally call the
`printf` function. On the last line we subtract the string length, `hello_len`,
from the return value of `printf`.

Assuming the above code resides in the file `hello64_libc.asm`, we can assemble
and link it with

	:::shell
	nasm -f elf64 -o hello64_libc.o hello64_libc
	gcc -o hello64_libc hello64_libc.o


The ELF executable I get on my machine is 8696 bytes in size, and 6328 without
the symbol table. If we thought 1048 was too much for a simple Hello World
application, the libc example is 8 times bigger. And without symbols, you can
see that we are wasting about 8K by relying on the Standard C Library.

A somewhat intermediate approach is to drop the main function and only use the
`printf` function from `libc`. The advantage is a reduced file size, since our
executable only depends on the Standard C Library. However, as discussed above,
we lose an important clean-up process that can be convenient, if not necessary,
at times.

	#!nasm
	global _start

	%include "../syscalls.inc"

	extern printf

	;
	; Initialised data goes here
	;
	SECTION .data
	hello           db  "Hello World!", 10, 0   ; const char *
	hello_len       equ $ - hello - 1           ; size_t
	;
	; Code goes here
	;
	SECTION .text

	_start:
	    ; printf(hello) - hello_len;
	    lea     rdi, [hello]
	    xor     rax, rax
	    call    printf
	    sub     rax, hello_len

	    ; syscall(SYS_EXIT, rax - hello_len)
	    push    rax
	    mov     rax, SYS_EXIT
	    pop     rdi
	    syscall
*hello64_libc2.asm*

Note how, on lines 1 and 18, we removed the main function and reintroduced the
`_start` symbol to tell NASM where the entry point is. Thus, execution of our
application now starts at line 20\. Here we prepare to call the `printf`
function from `libc` (lines 20 to 22), we compute the exit code (line 23) and we
store it in the stack. Now there is no Standard C Library framework to terminate
the execution for us, since we cannot return from the non-existent main
function, and therefore we have to make a call to `SYS_EXIT` ourselves (lines 26
to 29).

Assuming this code resides in the file `hello64_libc2`, we assemble and link
with the commands

	:::shell
	nasm -f elf64 -o hello64_libc2.o hello64_libc2
	ld -s -o hello64_libc2 hello64_libc.o -I/lib64/ld-linux-x86-64.so.2


Checking the file size, this is what I get on my machine now

	:::text
	$ wc -c < hello64_libc2
	2056


i.e. about a third of the "full" `libc` example above. There is something we can
still do with `strip`, namely determine which sections are not needed. After
linking with `ld`, the ELF I get has the following sections

	:::text
	$ readelf -S hello64_libc2 | grep [.]
	  [ 1] .interp           PROGBITS         0000000000400158  00000158
	  [ 2] .hash             HASH             0000000000400178  00000178
	  [ 3] .dynsym           DYNSYM           0000000000400190  00000190
	  [ 4] .dynstr           STRTAB           00000000004001c0  000001c0
	  [ 5] .gnu.version      VERSYM           00000000004001de  000001de
	  [ 6] .gnu.version_r    VERNEED          00000000004001e8  000001e8
	  [ 7] .rela.plt         RELA             0000000000400208  00000208
	  [ 8] .plt              PROGBITS         0000000000400220  00000220
	  [ 9] .text             PROGBITS         0000000000400240  00000240
	  [10] .eh_frame         PROGBITS         0000000000400260  00000260
	  [11] .dynamic          DYNAMIC          0000000000600260  00000260
	  [12] .got.plt          PROGBITS         00000000006003a0  000003a0
	  [13] .data             PROGBITS         00000000006003c0  000003c0
	  [14] .shstrtab         STRTAB           0000000000000000  000003ce


By trials and errors, I have discovered that I can get rid of `.hash`,
`.gnu.version` and `.eh_frame` while still getting a valid ELF executable that
does its job. To get rid of these sections one can use the command

	:::shell
	strip -R .hash -R .gnu.version -R .eh_frame hello64_libc2


which yields an executable of 1832 bytes.

# Conclusions

With the above examples, we have seen that, if our real goal is that of coding a
Hello World application meant to run on an architecture with the x86_64
instruction set, assembly is the best shot we have. Chances are, if you are
coding an application, it is more complex than just printing a string on screen.
Even pretending for a moment that you don't care about the portability of your
code, there are certainly some benefits from linking your application with gcc
and letting the Standard C Library do some clean-up work for you. We will have
the chance to see this last point from a close-up perspective in a future post.
So take this current post as a reference point where you can look back when you
need to recall the basics of writing a 64-bit assembly application for the Linux
OS.
