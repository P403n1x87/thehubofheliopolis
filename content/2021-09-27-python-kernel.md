Title:    Spy on Python down to the Linux kernel level
Authors:  Gabriele N. Tornetta
Date:     2021-09-27 11:56:00 +0100
Category: Programming
Tags:     python, profiling
art:      bust-perf-issues/austin_sign.png
pic:      python-kernel
Summary:  Observability into native call stacks requires some compromise. In this post I explain what this actually means for a Python tool like Austin.


When I conceived the design of [Austin][austin] for the first time, I've sworn
to always adhere to two guiding principles:

- no dependencies other than the standard C library (and whatever system calls
  the OS provides);
- minimal impact on the tracee, even under high sampling frequency.

Let me elaborate on why I decided to stick to these two _rules_. The first one
is more of a choice of simplicity. The power horse of Austin is the capability
of reading the private memory of any process, be it a child process or not. Many
platforms provide the API or system calls to do that, some with more security
gotchas than others. Once Austin has access to that information, the rest is
plain C code that makes sense of that data and provides a meaningful
representation to the user by merely calling `libc`'s `fprintf` on a loop.

The second guiding principle is what everybody desires from observability tools.
We want to be able to extract as much information as possible from a running
program, perturbing it as little as possible as to avoid skewed data. Austin can
make this guarantee because reading VM memory does not require the tracee to be
halted. Furthermore, the fact that Python has a [GIL][gil] implies that a simple
Python application will run on at most one physical core. To be more precise, a
normal, pure-Python application would not spend more CPU time than wall-clock
time. Therefore, on machines with multiple cores, even if Austin ends up acting
like a busy loop at high sampling frequencies and hogging a physical core, there
would still be plenty of other cores to run the Python application unperturbed
and unaware that is being spied on. Even for [multiprocess][mp] applications,
the expected impact is minimal, for if you are running, say, a uWSGI server on a
64-core machine, you wouldn't lose much if Austin hogs one of them. Besides, you
probably don't need to sample at very high frequences (like once every 50
microseconds), but you could be happy with, e.g. 1000 Hz, which is still pretty
high, but would not cause Austin to require an entire core for itself.

When you put these two principles together you get a tool that compiles down to
a single tiny binary and that has minimal impact on the tracee at runtime. The
added bonus is that it doesn't even require any instrumentation! These are
surely ideal features for an observability tool that make Austin very well
suited for running in a production environment.

But Austin strengths are also its limitations unfortunately. What if our
application has parts written as Python extensions, e.g. native [C/C++
extensions][ext], [Cython][cython], [Rust][pyo3], or even [assembly][asm]? By
reading a process private VM, Austin can only reconstruct the pure-Python call
stacks. To unwind the native call stacks, Austin would need to use some heavier
machinery. Forget about using a third-party library for doing that, which would
violate the first principle, the more serious issue here is that there are
currently no ways of avoiding the use of system calls like [`ptrace(2)`][ptrace]
from user-space. This would be a serious violation of the second principle. Why?
Because stack unwinding using `ptrace` requires threads to be halted, thus
causing a non-negligible impact on the tracee. Besides, stack unwinding is not
exactly straight-forward on every platform to implement.

The compromise is [austinp][austinp], a _variant_ of Austin that can do native
stack unwinding, _just_ on Linux, using [`libunwind`][libunwind] and `ptrace`.
This tool is to be used when you really need to have observability into native
call stacks, as the use of `ptrace` implies that the tracee will be impacted to
some extent. This is why, be default, `austinp` samples at a much lower rate.
This doesn't mean that you cannot use this tool in a production environment, but
that you should be aware of the potential penalties that come with it. Many
observability tools from the past relied on `ptrace` or similar to achieve their
goal, and `austinp` is just a (relatively) new entry into that list. More modern
solutions rely on technologies like [eBPF][ebpf] to provide efficient
observability into the Linux kernel, as well as into user-space.

Speaking of the Linux kernel, eBPF is not the only way to retrieve kernel
stacks. In the future we might have a variant of Austin that relies on eBPF for
some heavy lifting, but for now `austinp` leverages the information exposed by
[`procfs`][procfs] to push stack unwinding down to the Linux kernel level. The
`austinp` variant has the same CLI of Austin, but with the extra option `-k`,
which can be used to sample kernel stacks alongside native ones. I am still to
find a valid use-case for wanting to obtain kernel observability from a Python
program, but I think this could be an interesting way to see how the interpreter
interacts with the kernel; and perhaps someone might find ways of inspecting the
Linux kernel performance by coding a simple Python script rather than a more
verbose C equivalent.

You can find some examples of `austinp` in action on my [Twitter
account][twitter]. This, for example, is what you'd get for a simple
[scikit-learn][sklearn] classification model, when you open the collected
samples via the [Austin VS Code][vscode] extension:

<blockquote class="twitter-tweet" data-theme="dark"><p lang="en" dir="ltr">The latest development builds of <a href="https://twitter.com/AustinSampler?ref_src=twsrc%5Etfw">@AustinSampler</a>, including the austinp variant for native stack sampling on Linux are now available from <a href="https://twitter.com/github?ref_src=twsrc%5Etfw">@github</a> releases <a href="https://t.co/nBfzm3mDng">https://t.co/nBfzm3mDng</a>. <a href="https://t.co/IjVfAm1hRk">pic.twitter.com/IjVfAm1hRk</a></p>&mdash; Gabriele Tornetta 🇪🇺 🇮🇹 🇬🇧 (@p403n1x87) <a href="https://twitter.com/p403n1x87/status/1435569784620470283?ref_src=twsrc%5Etfw">September 8, 2021</a></blockquote> <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

If you want to give `austinp` a try you can follow the instructions on the
[README][austinp] for compiling from sources, or download the pre-built binary
from the the [Development build][dev]. In the future, `austinp` will be
available from ordinary releases too!


[austin]: https://github.com/p403n1x87/austin
[gil]: https://realpython.com/python-gil/
[mp]: https://docs.python.org/3/library/multiprocessing.html
[ext]: https://docs.python.org/3/extending/extending.html
[cython]: https://cython.org/
[pyo3]: https://github.com/PyO3/pyo3
[asm]: {filename}2018-03-24-asn-python.md
[austinp]: https://github.com/P403n1x87/austin/tree/devel#native-frame-stack
[libunwind]: https://www.nongnu.org/libunwind/
[ptrace]: https://man7.org/linux/man-pages/man2/ptrace.2.html
[ebpf]: https://ebpf.io/
[procfs]: https://man7.org/linux/man-pages/man5/proc.5.html
[sklearn]: https://scikit-learn.org/stable/
[twitter]: https://twitter.com/p403n1x87
[vscode]: [https://marketplace.visualstudio.com/items?itemName=p403n1x87.austin-vscode]
[dev]: https://github.com/P403n1x87/austin/releases/tag/dev