---
pic     : containers
layout  : post
title   : What Actually Are Containers?
author  : Gabriele N. Tornetta
date    : 2018-08-04 18:42:00 +0100
github  : P403n1x87/asm/tree/master/chroot
toc     : true

categories:
  - Linux

tags:
  - containers
  - jails

excerpt: >
  Containers are the big thing of the moment. It is quite common to find blog
  posts and articles that explain what containers are _not_:  "containers are
  not virtual machines". Just what _are_ they then? In this post we embark on a
  journey across some of the features of the Linux kernel to unveil the mystery.
---

# Introduction

When I first heard about containers, I turned to my favourite search engine to
find out more about them and what they are. Most of the resources I have read
through, though, seemed to put a great emphasis on what containers are **not**.
Containers are like virtual machines, but are **not** virtual machines.

So, what actually **are** they? After many unhelpful reads, the first good blog
post that I've come across and that explains what containers indeed are is [What
even is a container](https://jvns.ca/blog/2016/10/10/what-even-is-a-container/)
by Julia Evans. If you go and read through that post (and I do recommended that
you do!), you will immediately learn that a container is like a cauldron where
you mix in the essential ingredients for a magic potion. Only in this case, the
ingredients are Linux kernel features.

If many posts on containers make it sounds like they are some sort of black
magic (how can you have a _lightweight_ virtual machine?!), the aim of this post
is to show that the idea behind them is quite simple and made possible by a few
Linux kernel features, like **control groups**, **chroot** and **namespaces**. I
will discuss each of them in turn in this post, but you should also be aware
that there are other kernel features involved in containers to make them robust
and secure. These other aspects, however, will be part of a separate post. Here
we shall just focus on the essential ingredients that can allow you to literally
handcraft and run something that you may call a container, in the sense that is
commonly used these days.


## Containers Defined

Before we progress any further, I believe that we should take a moment to agree
on the meaning that we should attach to the word _container_. Much of the
confusion, in my opinion, arises from the many different definitions that are
out there. According to
[Wikipedia](https://en.wikipedia.org/wiki/Operating-system-level_virtualization),
_containers_ ...

> ... may look like real computers from the point of view of programs running in
> them. A computer program running on an ordinary operating system can see all
> resources ... of that computer. However, programs running inside a container
> can only see the container's contents and devices assigned to the container.

My way of paraphrasing this definition is the following: a container is a main
process that runs in user-space that gives you the impression that you are
running an operating system with its own view of the file system, processes,
etc... on top of the operating system that is installed on the machine. In this
sense, a container _contains_ part of the host resources and hosts its own
system and user applications.

## A Note on Operating Systems

Another cause of confusion, sometimes, is the definition of _operating system_
itself, so before moving on, I want to make sure we agree on this too. An
operating system can be thought as a _nut_. At its core we have, well, the
kernel, which is in direct control of the hardware. On its own, the kernel is a
_passive_ component of an operating system. When an operating system is booted,
the kernel is the first part that gets loaded into memory and it quietly sits
there. Its purpose is to provide many "buttons and levers" (the _ABI_) that just
wait to be pushed and pulled to operate the hardware and provide services to
system and user applications. Around the kernel one usually finds, surprise
surprise, a shell. You might be familiar with Bash, Ksh, Zsh, etc... which allow
you to manipulate the file system (create, copy, move, delete files from disk),
launch applications etc ... . Some of these applications are included with the
operating system and build on top of the kernel services to provide basic
functionalities (e.g. most if not all the standard Unix tools). Such
applications are known as _system application_. Other software, like text
editors, games, web browsers and alike are _user applications_. In some cases,
it is hard to decide between system and user applications, as the line between
them is not very clear and open to debate. However, once you decide on what
works for you in terms of _system applications_, an operating system becomes the
combination of them and the kernel. Thus, Linux is just a _kernel_ and not an
operating system. On the other hand, Ubuntu _is_ an example of a (Linux-based)
operating system, since a typical Ubuntu installation includes the compiled code
of the Linux kernel together with system applications.

How do we tell which operating system we are currently running? Most Linux-based
operating system have some files in the '/etc' folder that contains information
about the distribution name and the installed version. For example, on
Debian-based distributions, this file is typically named `os-release`. In my
case, this is what I get if I peek at its content with `cat`:

{% terminal %}
$ cat /etc/os-release
NAME="Ubuntu"
VERSION="18.04 LTS (Bionic Beaver)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 18.04 LTS"
VERSION_ID="18.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
VERSION_CODENAME=bionic
UBUNTU_CODENAME=bionic
{% endterminal %}


# Creating Jails With `chroot`

One of the earliest examples of "containers" was provided by the use of
`chroot`. This is a system call that was introduced in the BSD in 1982 and all
it does is to change the apparent root directory for the process it is called
from, and all its descendant processes.

How can we use such a feature to create a container? Suppose that you have the
root file system of a Linux-based operating system in a sub-folder in your file
system. For example, the new version of your favourite distribution came out and
you want to try the applications it comes with. You can use the `chroot` wrapper
application that ships with most if not all Unix-based operating systems these
days to launch the default shell with the apparent root set to
`~/myfavedistro-latest`. Assuming that your favourite distribution comes with
most of the standard Unix tools, you will now be able to launch applications
from its latest version, using the services provided by the Linux kernel of the
host machine. Effectively, you are now running an instance of a different
operating system that is using the kernel loaded at boot time from the host
operating system (some sort of Frankenstein OS if you want).

Does what we have just described fit into the above definition of _container_?
Surely the default shell has its own view of the file system, which is a proper
restriction of the full file system of the host system. As for other resources,
like peripherals etc..., they happen to coincide with the host system, but at
least something is different. If we now look at the content of the `os-release`
file in the `/etc` folder (or the equivalent for the distribution of your
choice), you will quite likely see something different from before, so indeed we
have a running instance of a different operating system.

The term that is usually associated to `chroot` is _jail_ rather than
_container_ though. Indeed, a process that is running within a new apparent root
file system cannot see the content of the parent folders and therefore it is
confined in a corner of the full, actual file system on the physical host. The
modified environment that we see from a shell started with chroot is sometimes
referred to as a _chroot jail_. But perhaps another reason why the term _jail_
is being used is that, without the due precautions, it is relatively easy to
break out of one (well, OK, maybe that's not an official reason).

If the above discussion sounds a bit too abstract to you then don't worry
because we are about to get hour hands dirty with `chroot`.

## A Minimal `chroot` Jail

Since a `chroot` jail is pretty much like a _Bring Your Own System Application_
party, with the kernel kindly offered by the host, a minimal `chroot` jail can
be obtained with just the binary of a shell, and just a few other binary files.
Let's try and create one with just `bash` in it then. Under the assumption
that you have it installed on your Linux system, we can determine all the
shared object the `bash` shell depends on with `ldd`

{% terminal %}
$ ldd `which bash`
        linux-vdso.so.1 =>  (0x00007ffca3bca000)
        libtinfo.so.5 => /lib/x86_64-linux-gnu/libtinfo.so.5 (0x00007f9605411000)
        libdl.so.2 => /lib/x86_64-linux-gnu/libdl.so.2 (0x00007f960520d000)
        libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f9604e2d000)
        /lib64/ld-linux-x86-64.so.2 (0x00007f960563a000)
{% endterminal %}

So let's create a folder that will serve as the new root file system, e.g.
`~/minimal`, and copy the bash executable in it, together with all its
dependencies. Copy the `bash` executable inside `~/minimal/bin`, the libraries
from `/lib` into `~/minimal/lib` and those from `/lib64`into `~/minimal/lib64`.
Then start the `chroot` jail with

{% terminal # %}
chroot ~/minimal
{% endterminal %}

You should now have a running bash session with a vanilla prompt format that
looks like this

{% terminal # %}
bash-4.4#
{% endterminal %}

Note that `chroot` is being executed as the `root` user. This is because, under normal
circumstances, only `root` has the POSIX _capability_ of calling the
`SYS_CHROOT` system call.

> To see the current capabilities of a user one can use the `capsh --print`
  command. The `Bounding set` line shows the capabilities that have been
  inherited and that can be granted to a process from the current user.
  Capabilities represent another feature that is relevant for containers. They
  will be discussed in a separate post.

If you now play around a bit with this bash session, you will realise pretty
quickly that there isn't much that you can do. Most of the standard Unix tools
are not available, not even `ls`. This container that we created as a `chroot`
jail is indeed minimal.

## A More Interesting Example

Ubuntu has, since version 12.04, released base images of the operating system.
These are just root file system images in the format of a compressed tarball.
Suppose that a new stable version has come out and you want to give it a try
before you upgrade your system. One thing you can do is to go to the [Ubuntu
Base releases](http://cdimage.ubuntu.com/ubuntu-latest/releases/) page and
download the image that you want to test. Extract the content of the tarball
somewhere, e.g. `~/ubuntu-latest` and "run" it with `chroot`

{% terminal # %}
chroot ~/ubuntu-latest
{% endterminal %}

We are now running an instance of a new version of Ubuntu. To check that this is
indeed the case, look at the output of `cat /etc/os-release`. Furthermore, we
now have access to all the basic tools that make up the Ubuntu operating system.
For instance you could use aptitude to download and install new packages, which
could be useful to test the latest version of an application.

If you intend to do some serious work with these kinds of `chroot` jails, keep
in mind that some of the pseudo-file systems won't be available from within the
jail. That's why you would have to mount them manually with

{% terminal # %}
mount -t proc proc proc/
mount -t sysfs sys sys/
mount -o bind /dev dev/
{% endterminal %}

This way you will be able to use, e.g., `ps` to look at the currently running
processes.

## Leaky Containers

With the simplicity of `chroot` jails comes many issues that make these kind of
"containers" _leaky_. What do I mean by this? Suppose that you want to
_containerise_ two resource-intensive applications into two different `chroot`
jails (for example, the two applications, for some reasons, require different
Linux-based operating systems). A typical example these days is that of
microservices that we would like to run on the same host machine. When the first
microservice fires up, it starts taking all the system resources (like CPU time
for instance), leaving no resources for the second microservice. The same can
happen for network bandwidth utilisation or disk I/O rates.

Unfortunately, this issue cannot be addressed within `chroot` jails, and their
usefulness is somewhat restricted. Whilst we can use it to create some sort of
"ancestral" containers, this is not the solution we would turn to in the long
run.

Another serious issue with a poorly implemented `chroot` jail is the dreaded
S-word: _security_. If nothing is done to prevent the user of the jail from
calling certain system calls (e.g. `chroot` itself), it is relatively
straightforward to _break out_ of it. Recall how the `chroot` wrapper utility
requires `root` privileges to be executed. When we launched a bash session
within the Ubuntu Base root file system, we were logged in as the root user.
Without any further configuration, nothing will prevent us from coding a simple
application that performs the following steps from within the jail:

1. Create a folder with the `mkdir` system call or Unix wrapper tool.
2. Call the `chroot` system call to change the apparent root to the newly
created folder.
3. Attempt to navigate sufficiently many levels up to hit the actual file system
root.
4. Launch a shell.

Why does this work? A simple call to the `chroot` system call only changes the
apparent root file system, but doesn't actually change the current working
directory. The Unix `chroot` wrapper tool performs a combination of `chdir`
_followed_ by `chroot` to actually put the calling process inside the jail.

> A minimal version of the `chroot(2)` utility written in x86-64 assembly code
  can be found in the
  [`minichroot.asm`](https://github.com/P403n1x87/asm/blob/master/chroot/minichroot.asm)
  source file within the GitHub repository linked to this post.

A call to `chroot` which is not preceded by a call to `chdir` moves the jail
boundary _over_ the current location down another level, so that we are
effectively out of the jail. This means that we can `chdir` up many times now to
try and hit the actual root of the host file system. Now run a shell session and
bang! We have full control of the host file system under the root user! Scary,
isn't it?

> If you want to give this method a try, have a look at the
  [`jailbreak.asm`](https://github.com/P403n1x87/asm/blob/master/chroot/jailbreak.asm)
  source file within the GitHub repository linked to this post.

A less serious matter, but still something that you might want to address, is
that, after we have mounted the `proc` file system within the jail, the view of
the running processes from within the jail is the same as the one from the host
system. Again, if we do nothing to strip down capabilities from the `chroot`
jail user, any process on the host machine can easily be killed (in the best
hypothesis) by the jail user. Indeed, `chroot` containers really require a lot
of care to prevent unwanted information from leaking. That is why present days
containers make use of a different approach to guarantee "airtight" walls, as we
shall soon see.


# Control Groups

As we have argued above, when we make use of containers we might want to run
multiple instances of them on the same machine. The problem that we face is
physical resource sharing among the containers. How can we make sure that a
running instance of a containerised process doesn't eat up all the available
resources from the host machine?

The answer is provided by a feature of the Linux kernel known as **control
groups**. Usually abbreviated as `cgroups`, control groups  were initially
released in 2007, based on earlier work of Google engineers, and originally
named _process containers_.

Roughly speaking, _cgroups_ allow you to limit, account for and isolate system
resources usage among running processes. As a simple example, consider the
scenario where one of your applications has a bug and starts leaking memory in
an infinite loop. Slowly but inevitably, your process ends up using all the
physical memory available on the machine it is running on, causing some of the
other processes to be killed at random by the OOM (Out of Memory) killer or, in
the worst case, crashing the entire system. If only you could assign a slice of
memory to the process that you want to test, then OOM killer would get rid of
only your faulty process, thus preventing your entire system from collapsing and
allowing the other applications to run smoothly without consequences. Well, this
is exactly one of the problems that *cgroups* allow you to solve.

But physical memory is only one of the aspects (or _subsystem_, in the language
of _cgroups_; another term that is used interchangeably is _controller_) that
can be limited with the use of control groups. CPU cycles, network bandwidth,
disk I/O rate are other examples of resources that can be accounted for with
control groups. This way you can have two or more CPU-bound applications running
happily on the same machine, just by splitting the physical computing power
among them.

## A Hierarchy of cgroups

Linux processes are organised in a hierarchical structure. At boot, the `init`
process, with PID 1, is spawned, and every other process originates from it as a
child process. This hierarchical structure is visible from the virtual file
system mounted at `/proc`.

Cgroups have a similar hierarchical structure but, contrary to processes (also
known as _tasks_ in _cgroup_-speak), there may be _many_ of such hierarchies of
cgroups. This is the case for cgroups v1, but starting with version 2,
introduced in 2015, cgroups follow a unified hierarchic structure. It is
possible to use the two at the same time, thus having a hybrid cgroups resource
management, even though this is discouraged.

Every cgroups inherits features from the parent cgroups and in general they can
get more restrictive the further you move down the hierarchy, without the
possibility of having overrides. Processes are then spawned or moved/assigned to
cgroups so that each process is in exactly one cgroup at any given time.

This is, in a nutshell, what cgroups and cgroups2 are. A full treatment of
cgroups would require a post on its own and it would take us off-topic. If you
are curious to find out more about their history and their technical details,
you can have a look at the official documentation
[here](https://www.kernel.org/doc/Documentation/cgroup-v1/cgroups.txt) and
[here](https://www.kernel.org/doc/Documentation/cgroup-v2.txt).

## How to Work with Control Groups

Let's have a look at how to use cgroups to limit the total amount of physical
(or resident) memory that a process is allowed to use. The example is based on
cgroups v1 since they are still in use today even though cgroups v2 are
replacing them and there currently is an on-going effort of migrating from v1 to
v2.

Since the introduction of cgroups in the Linux kernel, _every_ process belongs
to one and only one cgroup at any given time. By default, there is only one
cgroup, the _root_ cgroup, and every other process, together with its children,
is in it.

Control groups are manipulated with the use of file system operations on the
cgroup mount-point (usually `/sys/fs/cgroup`). For example, a new cgroup can be
created with the `mkdir` command. Values can be set by writing on the files that
the kernel will create in the subfolder, and the simplest way is to just use
`echo`. When a cgroup is no longer needed, it can be removed with `rmdir` (`rm
-r` should not be used as an alternative!). This will effectively deactive the
cgroup only when the last process in it has terminated, or if it only contains
zombie processes.

As an example, let's see how to create a cgroup that restricts the amount of
total physical memory processes can use.

{% terminal # %}
mkdir /sys/fs/cgroup/memory/mem_cg
echo 100m > /sys/fs/cgroup/memory/mem_cg/memory.limit_in_bytes
echo 100m > /sys/fs/cgroup/memory/mem_cg/memory.memsw.limit_in_bytes
{% endterminal %}

> If `memory.memsw.*` is not present in `/sys/fs/cgroup/memory`, you might need
  to enable it on the kernel by adding the parameters `cgroup_enable=memory
  swapaccount=1` to, e.g., GRUB's _kernel line_. To do so, open
  `/etc/default/grub` and append these parameters to
  `GRUB_CMDLINE_LINUX_DEFAULT`.

Any process running in the `mem_cg` cgroup will be constrained to a total amount
(that is, physical plus swap) of memory equal to 100 MB. When a process gets
above the limit, the OOM killer will get rid of it. To add a process to the
`mem_cg` cgroup we have to write its PID to the `tasks` file, e.g. with

{% terminal # %}
echo $$ > /sys/fs/cgroup/memory/mem_cg/tasks
{% endterminal %}

This will put the currently running shell into the `mem_cg` cgroup. When we want
to remove the cgroup, we can just delete its folder with

{% terminal # %}
rmdir /sys/fs/cgroup/memory/mem_cg
{% endterminal %}

Note that, even if fully removed from the virtual file system, any removed
cgroups remain active until all the associated processes have terminated or have
become zombies.

Alternatively, one can work with cgroups by using the tools provided by
`libcgroup` (Red Hat), or `cgroup-tools` (Debian). Once installed with the
corresponding package managers, the above commands can be replaced with the
following, perhaps more intuitive ones:

{% terminal # %}
cgcreate -g memory:mem_cg
cgset -r memory.limit_in_bytes=100m
cgset -r memory.memsw.limit_in_bytes=100m
cgclassify -g memory:mem_cg $$
cgdelete memory:mem_cg
{% endterminal %}

One can use `cgexec` as an alternative to start a new process directly within a
cgroup:

{% terminal # %}
cgroup -g memory:mem_cg /bin/bash
{% endterminal %}

We can test that the memory cgroup we have created works with the following
simple C program

{% highlight C %}
#include "stdlib.h"
#include "stdio.h"
#include "string.h"

void main() {
  int    a      = 0;
  char * buffer = NULL;

  while (++a) {
    buffer = (char *) malloc(1 << 20);
    if (buffer) {
      printf("Allocation #%d\n", a);
      memset(buffer, 0, 1 << 20);
    }
  }

  return;
}
{% endhighlight %}

We have created an infinite loop in which we allocate chunks of 1 MB of memory
at each iteration. The call to `memset` is a trick to force the Linux kernel to
actually allocate the requested memory under the copy-on-write strategy.

Once compiled, we can run it into the `mem_cg` cgroup with

{% terminal # %}
cgexec -g mem_cg ./a.out
{% endterminal %}

We expect to see about 100 successful allocations and after that the OOM killer
intervenes to stop our processes, since it would have reached the allocated
memory quota by then.

Imagine now launching a `chroot` jail inside a memory cgroup like the one we
created above. Every application that we launch from within it is automatically
created inside the same cgroup. This way we can run, e.g., a microservice and we
can be assured that it won't eat up all the available memory from the host
machine. With a similar approach, we could also make sure that it won't reserve
all the CPU and its cores to itself, thus allowing other processes (perhaps in
different jails/containers) to run simultaneously and smoothly on the same
physical machine.


# Linux Namespaces

The description of Linux namespaces given by the dedicated manpage sums up the
concept pretty well:

> A namespace wraps a global system resource in an abstraction that
  makes it appear to the processes within the namespace that they have
  their own isolated instance of the global resource.  Changes to the
  global resource are visible to other processes that are members of
  the namespace, but are invisible to other processes.  One use of
  namespaces is to implement containers.

So no questions asked about why Linux namespaces were introduced in the first
place. As the description says, they are used to allow processes to have their
own copy of a certain physical resource. For example, the most recent versions
of the Linux kernel allow us to define a namespace of the **network** kind, and
every application that we run under it will have its own copy of the full
network stack. We have pretty much a rather lightweight way of virtualising an
entire network!

Linux namespaces represent a relatively new feature that made its first
appearance in 2002 with the **mount** kind. Since there were no plans to have
different kinds of namespaces, at that time the term _namespace_ was synonym of
_mount_ namespace. Beginning in 2006, more kinds were added and, presently,
there are plans for new kinds to be developed and included in future releases of
the Linux kernel.

If you really want to identify a single feature that makes modern Linux
container possible, namespaces is arguably the candidate. Let's try to see why.

## Some Implementation Details

In order to introduce namespaces in Linux, a new system call, `unshare`, has
been added to the kernel. Its use is "to allow a process to control its shared
execution context without creating a new process." (quoted verbatim from the
manpage of `unshare(2)`). What does this mean? Suppose that, at a certain point,
you want the current process to be moved to a new network namespace so that it
has its own "private" network stack. All you have to do is make a call to the
`unshare` system call with the appropriate flag set.

What if we do want to spawn a new process in a new namespace instead? With the
introduction of namespaces, the existing `clone` system call has been extended
with new flags. When `clone` is called with some of these flags set, new
namespaces of the corresponding kinds are created and the new process is
automatically made a member of them.

The namespace information of the currently running processes is stored in the
`proc` file system, under the new `ns` subfolder of every PID folder (i.e.
`/proc/[pid]/ns/`). This as well as other details of how namespaces are
implemented can be found in the
[`namespaces(7)`](http://man7.org/linux/man-pages/man7/namespaces.7.html)
manpage.

## How to Work with Namespaces

As with cgroups, an in-depth description of namespaces would require a post on
its own. So we will have a look at just one simple example. Since networks are
ubiquitous these days, let's try to launch a process that has its own
virtualised network stack and that is capable of communicating with the host
system via a network link.

This is the plan:

1. Create a linked pair of virtual ethernet devices, e.g. `veth0` and `veth1`.
2. Move `veth1` to a new network namespace
3. Assign IP addresses to the virtual NICs and bring them up.
4. Test that the can transfer data between them.

Here is a simple bash script that does exactly this. Note that the creation of a
network namespace requires a capability that normal Unix user don't usually
have, so this is why you will need to run them as, e.g., root.

{% highlight bash linenos %}
# Create a new network namespace
ip netns add test

# Create a pair of virtual ethernet interfaces
ip link add veth0 type veth peer name veth1

# Configure the host virtual interface
ip addr add 10.0.0.1/24 dev veth0
ip link set veth0 up

# Move the guest virtual interface to the test namespace
ip link set veth1 netns test

# Configure the guest virtual interface in the test namespace
ip netns exec test bash
ip addr add 10.0.0.2/24 dev veth1
ip link set veth1 up

# Start listening for TCP packets on port 2000
nc -l 2000
{% endhighlight %}

On line 2 we use the extended, namespace-capable version of `ip` to create a new
namespace of the network kind, called `test`. We then create the pair of virtual
ethernet devices with the command on line 5. On line 12 we move the `veth1`
device to the `test` namespace and, in order to configure it, we launch a bash
session inside `test` with the command on line 15. Once in the new namespace we
can see the `veth1` device again, which has now disappeared from the default
(also known as _global_) namespace. You can check that by opening a new terminal
and typing `ip link list`. The `veth1` device should have disappeared after the
execution of the command on line 12.

We can then use `netcat` to listen to TCP packets being sent on port 2000 from
within the new namespace (line 20). On a new bash session in the default
namespaces, we can start `netcat` with

{% terminal $ %}
nc 10.0.0.2 2000
{% endterminal $ %}

to start sending packets to the new namespace `test` via the link between
`veth0` and `veth1`. Everything that you type should now be echoed by the bash
session in the `test` namespace after you press Enter.


# Putting It All Together

Now let's see how to put all the stuff we have discussed thus far together to
handcraft some more (better) containers.

## Process Containment for `chroot` Jails

With our first attempt at manually crafting a container with `chroot`, we
discovered a few weaknesses of different nature that made the result quite
leaky. Let's try to address some of those issues, for instance the fact that all
the processes running on the host system are visible from within the container.
To this end, we shall make use of the Ubuntu Base image that we used in the
`chroot` section. We then combine `chroot` with namespaces in the following way.
Assuming that you have created the `test` network namespace as described in the
previous section, run

{% terminal # %}
unshare --fork -p -u ip netns exec test chroot ubuntu-latest
{% endterminal %}

The `--fork` switch is required by the `-p` switch because we want to spawn a
new bash session with PID 1, rather than within the calling process. The `-u`
switch will give us a new hostname that we are then free to change without that
affecting the host system. We then use the `ip` new capability of creating
namespaces of the network kind to create the Ubuntu Base `chroot` jail.

The first improvement is now evident. From inside the `chroot` jail, mount the
`proc` file system with, e.g.

{% terminal # %}
mount -t proc proc /proc
{% endterminal %}

and then look at the output of `ps aux`:

{% terminal %}
# ps -ef
UID        PID  PPID  C STIME TTY          TIME CMD
root         1     0  0 11:54 ?        00:00:00 /bin/bash -i
root         8     1  0 11:56 ?        00:00:00 ps -ef
{% endterminal %}

The bash session that we started inside the `chroot` jail has PID 1 and the `ps`
tool from the Ubuntu Base distribution has PID 8 and parent PID 1, i.e. the
`chroot` jail. That's all the processes that we can see from here! If we try to
identify this bash shell from the global namespace we find something like this

{% terminal %}
$ ps -ef | grep unshare | grep -v grep
root      5829  4957  0 12:54 pts/1    00:00:00 sudo unshare --fork -p -u ip netns exec test chroot ubuntu-latest
root      5830  5829  0 12:54 pts/1    00:00:00 unshare --fork -p -u ip netns exec test chroot ubuntu-latest
{% endterminal %}

PIDs in your case will quite likely be different, but the point here is that,
with namespaces, we have broken the assumption that a process has a _unique_
process ID.

## Wall Fortification

Whilst the process view problem has been solved (we can no longer kill the host
processes since we cannot see them), the fact that the `chroot` jail runs as
root still leaves us with the _jailbreak_ issue. To fix this we just use
namespaces again the way they where meant to be used originally. Recall that,
when they were introduced, namespaces were of just one kind: mount. In fact,
back then, namespaces was a synonym of _mount_ namespace.

The other ingredient that is needed to actually secure against jail breaking is
the `pivot_root` system call. At first sight it might look like `chroot`, but it
is quite different. It allows you to put the old root to a new location and use
a new mount point as the new root for the calling process.

The key here is the combination of `pivot_root` and the namespace of the kind
mount that allows us to specify a new root and manipulate the mount points that
are visible inside the container that we want to create, without messing about
with the host mount points. So here is the general idea and the steps required:

1. Start a shell session from a shell executable inside the root file system in
a mount namespace.
2. Unmount all the current mount points, including that of type `proc`.
3. Turn the Ubuntu Base root file system into a (bind) mount point
4. Use `pivot_root` and `chroot to swap the new root with the old one
5. Unmount the new location of the old root to conceal the full host file
system.

The above steps can be performed with the following initialisation script.

{% highlight bash %}
umount -a
umount /proc
mount --bind ubuntu-latest/ ubuntu-latest/
cd ubuntu-latest/
test -d old-root || mkdir old-root
pivot_root . old-root/
exec chroot . /bin/bash --init-file <(mount -t proc proc /proc && umount -l /old-root)
{% endhighlight %}

Copy and paste these lines in a file, e.g. `cnt-init.sh` and then run

{% terminal # %}
sudo unshare --fork -p -u -m ubuntu-latest/bin/bash --init-file cnt-init.sh
{% endterminal %}

You can now check that the `/old-root` folder is empty, meaning that we now have
no ways of accessing the full host file system, but only the corner that
corresponds to the content of the new root, i.e. the content of the
`ubuntu-latest` folder. Furthermore, you can go on and check that our recipe for
breaking out of a vanilla `chroot` jail does not work in this case, because the
jail itself is now an effective, rather than apparent, root!

# Conclusions

We have come to the end of this journey across the features of the Linux kernel
that make containers possible. I hope this has given you a better understanding
of what many people mean when they say that containers are like virtual
machines, but are _not_ virtual machine.

Whilst spinning containers by hand could be fun, and quite likely an interesting
educational experience for many, to actually produce something that is robust
and secure enough requires some effort. Even in our last examples there are many
things that need to be improved, starting from the fact that we would want to
avoid giving control of our containers to users as root. Despite all our effort
to improve containment of resources, an user logged in as root can still do some
nasty things (open lower-numbered ports and all such kind of businesses...). The
point here is that, if you need containers for production environments, you
should turn to well tested and established technologies, like LXC, Docker etc...
.
