Title:    My first close encounter with the Linux kernel source
Authors:  Gabriele N. Tornetta
Date:     2022-01-15 14:39:00 +0000
Github:   P403n1x87/bpf/tree/copy-from-user-remote
Category: Programming
Tags:     linux, bpf, r&d
pic:      linux-first-encounter
Summary:  I finally had the chance to set some time aside to touch the Linux kernel source, for fun and profit. This is the story of how I implemented a new BPF helper.

[TOC]

# Background

As you probably know if you've been on my blog before, I develop and maintain
[Austin][austin], a frame stack sampler for CPython which, in essence, is the
main material for building a zero-instrumentation, minimal impact sampling
profiler for Python. Recently I worked on a variant, [austinp][austinp], which
samples not only the Python stacks, but also native ones (optionally including
Linux kernel stacks as well). The reason why this is just a variant and not part
of Austin itself is because it violates two of its fundamental principles:
dependencies and impact. The `austinp` variant relies on `libunwind` to perform
native stack unwinding, which means that a. we have a dependency on a
third-party library and b. since `libunwind` relies on `ptrace`, `austinp` no
longer has the guarantee of minimal impact.

With the rapid and highly active development of [eBPF][bpf] in the Linux kernel,
`ptrace`-based stack unwinding might as well be considered a thing of the past.
One can exploit the BPF support for `perf_event` to implement a simple native
profiler [in just a few lines of C code][mybpf] with the support of
[libbpf][libbpf]. But for Austin to one day have a BPF variant, native stacks
alone are not enough. We would need a way to unwind the Python frame stack from
a BPF program, and at the moment of writing this is not quite yet possible. Why?
Because the BPF part of the Linux kernel lacks support for accessing the VM
space of a remote process. Indeed, the [`process_vm_readv`][process_vm_readv]
system call is the core functionality that makes Austin possible on Linux, and
unfortunately, as I discovered, there is no counterpart exposed to BPF at the
time of writing.

How do I know there is no such functionality in BPF-land yet? Back in September
2021 I sent [an email][september] to the BPF mailing list, asking if it was
possible to do what `process_vm_readv` does inside a BPF program. The answer I
received from the maintainer was negative, but it turned out I asked the
question at the right time, because the feature that was required to make this
possible, i.e. sleepable BPF programs, had just been introduced in the kernel.
Unfortunately, I coulnd't pick up the invite from the maintainers to prepare a
patch back then. I still had not experience with the Linux kernel, nor the time
to fully commit to the task, so I had to postpone this. The chance to actually
look into this came with the January R&D week. This post is a recollection of
the events of that week.


# Getting things started

So January came and along with it the R&D Week. I decided to use this time to
finally have a play with the Linux kernel, something that I wanted to do in a
long time. Now I had the chance to do that for fun, but also for profit as I
actually had a pretty concrete use case. The first step was of course to get the
development environment up. Since I didn't want to risk bricking my Linux
partition, I decided the best approach was to spin up a virtual machine.

I had a Ubuntu VM lying around from previous experiments with BPF and I thought
of using that. Soon I discovered that, whilst many tutorials use or recommend a
Ubuntu system for Linux kernel development, things are much smoother on Debian.
So my personal recommendation for anyone starting on the Linux kernel for the
first time, like me, is to use Debian.

But let's go in order. The first thing we want to do is get our hands on the
latest version of the Linux kernel source code. So install `git` along with
these other dependencies

    :::shell
    sudo apt-get install vim libncurses5-dev gcc make git libssl-dev bison flex libelf-dev bc dwarves

and clone the repository with

    :::shell
    mkdir kernel
    cd kernel
    git clone -b staging-testing git://git.kernel.org/pub/scm/linux/kernel/git/gregkh/staging.git
    cd staging

These steps are adapted from [this KernelNewbies page][knfirstpatchsetup], which
is the guide that I have used to get started.

The Linux kernel is highly (like, _very_ highly) configurable, depending your
system and your needs, but of course the source code comes with none. The next
step then is to make one. The guide recommends starting from the current
system's configuration as a base, which we can get with

    :::shell
    cp /boot/config-`uname -r`* .config

If the VM is running a not-so-recent build of the Linux kernel, it's perhaps
worth running `make olddefconfig` to get any new configuration options in. And
to speed the compilation process up a bit, we can use the current module
configuration with `make localmodconfig` to get rid of some of the defaults that
are not applicable to the current system.

> This is where things get a bit annoying if you are using Ubuntu instead of
> Debian. It turns out there are some options that involve security certificates
> that are best set to the empty string to allow the build steps to regenerate
> whatever is needed. So if you are using Ubuntu to experiment on the Linux
> kernel, you might want to set `CONFIG_SYSTEM_TRUSTED_KEYS`,
> `CONFIG_MODULE_SIG_KEY` and `CONFIG_SYSTEM_REVOCATION_KEYS` to `""`.

Before moving on, it might be a good
idea to change the value of `CONFIG_LOCALVERSION` to something else other than
the empty string, in case we end up overwriting the current Linux kernel. For
my experiments I have used `CONFIG_LOCALVERSION=p403n1x87`. This will show up
as a prefix in the kernel image name in the bootloader menu

<p align="center">
  <a href="{static}images/linux-first-encounter/grub.png" target="_blank"><img
    src="{static}images/linux-first-encounter/grub.png"
    alt="The custom Linux kernel build image in GRUB"
  /></a>
</p>

To make sure that everything is in order, and that you get GRUB menu entries
similar to the ones shown above we can try to compile the sources with

    :::shell
    make -j2 > /dev/null && echo "OK"

Feel free to replace the `2` with any other number that might be appropriate to
your system. This represents the number of parallel compilation processes that
are spawned, so it correlates with the number of cores that are available to
your VM. The `/dev/null` is there to suppress any output that goes to `stdout`,
which is not very instructive. This leaves us with more useful warnings and
errors that are spit out to `stderr`. If the compilation succeeeded we would
then see `OK` at the end of the output. If this is the case, we can proceed with
the installation with

    :::shell
    sudo make modules_install install

To boot into the newly compiled Linux kernel, simply reboot the VM with

    :::shell
    sudo reboot

We're now all set to start hacking the Linux kernel 🎉.


# Adding new bells and whistles

I spent the Monday of R&D Week getting my environment up and running and having
a first look at the structure of my local copy of the Linux kernel source
repository. The next day I started studying the parts that were relevant to my
goal, that is find out where the `process_vm_readv` system call is defined and
how it works internally. The Linux kernel source comes with `ctags` support for
easy navigation. However, if you do not want to install additional tools you can
make use of the [Elixir][elixir] project to find where symbols are defined and
referenced.

The `process_vm_readv` system call is defined in `mm/process_vm_access.c`.
Studying the content of this source carefully, we discover that memory is read
page-by-page using `copy_page_to_iter`. The system call is also generic in the
sense that it performs multiple operations, according to the number of `iovec`
elements that are passed to it. For my use case, I'm seeking to implement a
function with the signature

    :::c
    ssize_t process_vm_read(pid_t pid, void * dst, ssize_t size, void * user_ptr);

so that a possible implementation might have looked something like

    :::c
    ssize_t process_vm_read(pid_t pid, void * dst, ssize_t size, void * user_ptr) {
      struct iovec lvec, rvec;

      if (unlikely(size == 0))
        return 0;

      lvec = (struct iovec) {
        .iov_base = dst,
        .iov_len = size,
      }
      rvec = (struct iovec) {
        .iov_base = user_ptr,
        .iov_len = size,
      }

      return process_vm_rw(pid, &lvec, 1, &rvec, 1, 0, 0);
    }

This is indeed what I have started experimenting with. I added this function to
`mm/process_vm_access.c` and exposed it to BPF with the helper

    :::c
    BPF_CALL_4(bpf_copy_from_user_remote, void *, dst, u32, size,
        const void __user *, user_ptr, pid_t, pid)
    {
      if (unlikely(size == 0))
        return 0;

      return process_vm_read(pid, dst, size, user_ptr);
    }

    const struct bpf_func_proto bpf_copy_from_user_remote_proto = {
      .func		= bpf_copy_from_user_remote,
      .gpl_only	= false,
      .ret_type	= RET_INTEGER,
      .arg1_type	= ARG_PTR_TO_UNINIT_MEM,
      .arg2_type	= ARG_CONST_SIZE_OR_ZERO,
      .arg3_type	= ARG_ANYTHING,
      .arg4_type	= ARG_ANYTHING,
    };

To test this I wrote a simple C application that takes an integer from the
command line, stores it safely somewhere in its VM space and is kind enough to
tell us its PID and the VM address where we can find the "secret"

    :::c
    #include <stdio.h>
    #include <stdlib.h>
    #include <unistd.h>

    int main(int argc, char **argv)
    {
        if (argc != 2)
        {
            fprintf(stderr, "usage: secret <SECRET>\n");
            return -1;
        }

        int secret = atoi(argv[1]);

        printf("I'm process %d and my secret is at %p\n", getpid(), &secret);
        printf("%d %p\n", getpid(), &secret);

        for (;;)
            sleep(1);

        return 0;
    }

We can then write a simple BPF program that takes the PID and the address to
pass them to the new helper in the attempt to retrieve the secret value from the
remote target process

    :::c
    int secret;

    ...

    SEC("fentry.s/__x64_sys_write")
    int BPF_PROG(test_sys_write, int fd, const void *buf, size_t count)
    {
        int pid = bpf_get_current_pid_tgid() >> 32;

        if (pid != my_pid)
            return 0;

        long bytes;

        bytes = bpf_copy_from_user_remote(&secret, sizeof(secret), user_ptr, target_pid);
        bpf_printk("bpf_copy_from_user_remote: copied %d bytes", bytes);

        return 0;
    }

We are using `fentry` because it has a sleepable variant, `fentry.s`, and using
`sys_write` as our target system call. Every time this system call is called our
BPF program is executed. In this case we just run only if it was the associated
user-space process that made the call.

Unfortunately, when checking the result of the `bpf_printk` call from
`/sys/kernel/debug/tracing/trace_pipe`, I would always see `-14` (`-EFAULT`)
instead of the expected `4`. This is an indication that we are passing the wrong
memory addresses around. Further investigation led me to the conclusion that the
problem was with how I was using `process_vm_rw`. Indeed, the manpage of the
`process_vm_readv` system call clearly states that

> These system calls transfer data between the address space of the calling
> process ("the local process") and the process identified by pid ("the
> remote process"). The data moves directly between the address spaces of
> the two processes, without passing through kernel space.

The problem here is that the destination is a variable with a kernel-space
address, which would then fail the checks in `import_iovec` in the attempt to
copy the `struct iovec` data over from user-space into kernel-space. Looking at
how `process_vm_rw` is actually implemented, one can see that the local vectors
are turned into a `struct iov_iter`, so I though that all that was needed was to
create one from a `struct kvec` instead. My next attempt has then been

    :::c
    ssize_t process_vm_read(pid_t pid, void * dst, ssize_t size, void * user_ptr) {
      struct kvec lvec;
      struct iovec rvec;
      struct iov_iter;

      if (unlikely(size == 0))
        return 0;
      
      lvec = (struct kvec) {
        .iov_base = dst,
        .iov_len = size,
      };
      rvec = (struct iovec) {
        .iov_base = user_ptr,
        .iov_len = size,
      };

      iov_iter_kvec(&iter, READ, &lvec, 1, size);
      return process_vm_rw_core(pid, &iter, &rvec, 1, 0, 0);
    }

Progress! The return value of the BPF helper is now `4` as expected, but for
some reason the value read into `int secret` was always 0. 💥

While in the middle of my experiments, I sent a [new message][wednesday] to the
BPF mailing list on Wednesday, asking for feedback on my approach. I just wanted
to see if, generally, I was on the right track and what I was doing made any
sense. Clearly, my initial use of the details of `process_vm_readv` did not. On
Thurday evening a get the [reply of Kenny][kenny] from Meta, who showed me their
patch with a similar change. They used `access_process_vm` from `mm/memory.c`
instead, with the added bonus of requring a reference to a process descriptor
`struct task_struct` instead of a `pid`. This has the benefit, as Kenny
explained, to remove the ambiguity around `pid` which comes from the use of
namespaces. However, for my particular use case, I really need a `pid` (the
namespace information might also be given at some point). Looking back at the
notes that I have taken throughout the previous three days, I actually realised
that I had come across `access_process_vm` while poking around to find what else
was there. What threw me off was a misinterpretation of the comment that
preceded its definition

    :::c
    /*
    * Access another process' address space.
    * Source/target buffer must be kernel space,
    * Do not walk the page table directly, use get_user_pages
    */

Being a total Linux kernel newbie, I interpreted this as meaning that both
target and source should have been kernel-space addresses, which of course was
not my case. However, that comment refers to the `buf` argument, which makes a
lot of sense when you think of it, for the kernel-to-kernel interpretation does
not really fit with the name of the function. So I ditched my previous attempts
inside `mm/process_vm_access.c` and refactored my new BPF helper into

    :::c
    BPF_CALL_4(bpf_copy_from_user_remote, void *, dst, u32, size,
        const void __user *, user_ptr, pid_t, pid)
    {
      struct task_struct * task;

      if (unlikely(size == 0))
        return 0;

      task = find_get_task_by_vpid(pid);
      if (!task)
        return -ESRCH;

      return access_process_vm(task, (unsigned long) user_ptr, dst, size, 0);
    }

and success! The simple BPF program that we saw earlier is now able to correctly
read the secret from the target process! 🎉

> For the full BPF program sources, head over to my [bpf][copy-from-user-remote]
> repository.


# Use cases beyond Austin

Is this helper useful only for Austin? Not at all. Whilst there clearly is a use
case for Austin in the way that I described at the beginning of this post, the
new BPF helper opens up for many interesting observability applications. At the
end of the day, what this does is to allow BPF programs to read the VM of any
process on the system. Debugging of production systems should then be an idea
popping in your mind right now, and indeed this is the use case of Kenny and the
reason why they are proposing a similar BPF helper.

Think of a Python application, for example, running with CPython and native
extensions. Getting any sort of meaningful observability into them is generally
hard. This new helper might be able to, say, get the arguments of a (native)
function, interpret them as Python object, and return a meaningful
representation. The possibilities are virtually endless.


[austin]: https://github.com/p403n1x87/austin
[austinp]: https://github.com/P403n1x87/austin#native-frame-stack
[bpf]: https://ebpf.io/
[copy-from-user-remote]: https://github.com/P403n1x87/bpf/tree/copy-from-user-remote
[elixir]: https://elixir.bootlin.com/linux/latest/source
[knfirstpatchsetup]: https://kernelnewbies.org/OutreachyfirstpatchSetup?action=show&redirect=OPWfirstpatchSetup
[libbpf]: https://github.com/libbpf/libbpf
[kenny]: https://lore.kernel.org/bpf/20220113233708.1682225-1-kennyyu@fb.com/
[mybpf]: https://github.com/P403n1x87/bpf
[process_vm_readv]: https://man7.org/linux/man-pages/man2/process_vm_readv.2.html
[september]: https://lore.kernel.org/bpf/CAGnuNNt7va4u78rvPmusYnhXAuy5e9aRhEeO6HDqYUsH979QLQ@mail.gmail.com/T/
[wednesday]: https://lore.kernel.org/bpf/CAGnuNNtdvbk+wp8uYDPK3weGm5PVmM7hqEaD=Mg2nBT-dKtNHw@mail.gmail.com/
