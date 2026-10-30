Title:    The State of Python Profiling in 2026
Authors:  Gabriele N. Tornetta
Date:     2026-10-30 12:00:00 +0000
Category: Programming
Tags:     python, profiling, optimisation
art:      bust-perf-issues/austin_sign.png
pic:      state-of-python-profiling
Summary:  CPython now ships its own sampling profiler, free-threading is going mainstream, and coding agents have started reading profiles. In this post I look at where Python profiling stands today, compare Tachyon, py-spy, Scalene and Austin, and go through what's new in Austin 4.1.

Python profiling has changed more in the last two years than in the decade
before. CPython 3.14 gave external tools an official way to look inside a
running interpreter, and made `asyncio` task graphs inspectable from outside the
process. CPython 3.15 ships a sampling profiler in the standard library.
Free-threaded builds have gone from experiment to something people actually
deploy. And a growing share of the people reading profiles aren't people at all,
but coding agents.

This post looks at where things stand: what the main sampling profilers can do
today, where each one fits, and what changed in the latest release of Austin.

As many of you know, I've been working on Austin for the best part of eight
years now, so I have a view from the inside on how this landscape came to be,
and, naturally, a soft spot for one of the tools in it. I've tried to be fair to
the others: what I say about them comes from their own documentation and release
notes as of October 2026. If I've got something wrong, let me know and I'll fix
it.



[TOC]

# A Quick Map of the Landscape

Most profilers make two basic choices, and these choices explain most of the
differences between tools.

**Tracing or sampling.** A tracing (deterministic) profiler like `cProfile`
records every function call and return. You get exact call counts, but the
overhead changes the program's timing, sometimes a lot. A sampling profiler
looks at the call stack at regular intervals and builds a statistical picture
from those snapshots. You don't get call counts, but the program runs at close
to normal speed. I went into the differences between the two, and how they work
under the bonnet, in [an earlier post][deterministic-statistical].

**In-process or out-of-process.** An in-process profiler runs inside your
program, usually by starting it for you or being imported. An out-of-process
profiler is a separate program that reads the target's memory from outside.
Out-of-process tools can attach to something that's already running, like a
production server that started misbehaving an hour ago, without restarting it
or changing its code.

All four tools in this post are sampling profilers. Tachyon, py-spy and Austin
work from outside the process. Scalene works from inside.

## Why These Four

There are many more Python profilers than I can cover here, so I've picked the
ones I think are the most widely known and used, and that have a track record on
accuracy and overhead. That track record isn't just my opinion. The most
thorough comparison of Python profilers I know of, by the Scalene team at UMass
Amherst ([Berger, Stern and Altmayer Pizzorno, 2022][scalene-paper]), measured a
dozen of them on the longest-running benchmarks of the pyperformance suite. Its
conclusion was that sampling profilers are "both more efficient and often more
accurate" than tracing ones.

The two go together. A tracing profiler runs its own code on every function call
and return, inside your program, so it slows the program down, and not evenly:
code that makes many small calls is slowed down far more than code that makes
few, which skews the picture of where time is spent. The study found one
tracing profiler reporting that a function took 80% of the run time when it
actually took 25%. A sampling profiler stays out of the way of your code, so the
timings it reports are much closer to how the program behaves when nobody is
watching. In the study, Austin, py-spy and Scalene were among the profilers with
the lowest overhead in CPU mode, adding between 0% and 2% to the run time,
compared with 73% for `cProfile` and more than 200% for some others.

Tracing profilers still have their place: they count every call exactly, which
sampling can't do. If you need to know that a function was called 1,204 times,
use `cProfile`. If you need to know where the time goes, sample.

Tachyon is too new to have been part of that study, but as the profiler that now
ships with Python, it's the one many people will reach for first, so it belongs
here.

One notable absence is [pyflame](https://github.com/uber-archive/pyflame),
Uber's profiler from 2016. It was one of the first to sample Python stacks from
outside the process, and it deserves credit for showing that the approach works.
But it was Linux-only, its last changes date from 2019, before Python 3.8 was
released, and its repository is now archived and marked as no longer
maintained. I mention a few other good tools at the end of the post.

## Why Sampling Rate Matters

With a sampling profiler, the time attributed to a function is an estimate: the
fraction of samples it appears in, multiplied by the duration of the run. Like
any statistical estimate, its error shrinks as the number of samples grows,
roughly in proportion to 1/√n. Sampling 10 times faster gives you about three
times less noise from the same run, so short runs give stable results and
short-lived functions are less likely to be missed entirely.

So the maximum rate a profiler can sustain, without disturbing the target,
directly limits how accurate it can be.

That's why raw sampling speed has been a priority for Austin from the start, and
it's the reason it's written in C and does nothing but sample: every
microsecond saved per sample is another sample per second. Each release has
pushed this further. Austin 4.0 more than doubled the maximum sampling rate of
3.x, and 4.1 pushes it higher again (more on that below), with a default of
10,000 samples per second.

Tachyon's authors clearly think the same way: the profiler is named after the
hypothetical particle that travels faster than light. Its sampling core is
written in C too, and while its default rate is a more conservative 1,000 samples
per second, it's designed to be raised well beyond that. When a profiler that's
been around since 2018 and the one that has just joined the standard library
both put speed first, it's a good sign that sampling rate is finally getting the
attention it deserves.


# How We Got Here

Profiling Python from outside the process used to be close to a hack. CPython
made no promises about the layout of its internal structures, so tools like
Austin and py-spy had to copy large parts of the interpreter's private headers
for every Python version, and work out where the interesting fields were from
compiler- and platform-specific details. Every new release could break them, and
often did.

Those tools showed that the approach was worth it. Being able to attach to a
running process with no instrumentation and almost no overhead turned out to be
winning proposition in production, and evidently it made a strong case for
CPython to support out-of-process tools properly, rather than just tolerate
them.

Some of that work came directly from Austin. In 2021, I made three changes to
CPython, each to solve a problem I'd run into while working on Austin:

- **`co_qualname`** ([bpo-44530]). Code objects only carried a function's bare
  name, so an external profiler couldn't tell `Foo.run` from `Bar.run`, and
  their samples ended up merged. Since Python 3.11, code objects also carry the
  qualified name, and every out-of-process profiler can show it.
- **`native_thread_id`** ([bpo-43879]). To measure CPU time, a profiler needs the
  operating system's ID for each thread. On Linux, there was no direct way to
  find it from outside the process, so tools like Austin had to dig through
  glibc's internal thread structures to infer it.
  Since 3.11, the interpreter's thread state simply records it.
- **`Py_Version`** ([bpo-43931]). An exported symbol that lets external tools
  reliably tell which Python version a process is running. py-spy now uses it
  too.

Tachyon reads both `co_qualname` and `native_thread_id` today. In 2023 I
moved the fields that out-of-process tools rely on to the top of the
interpreter's structures ([gh-105271]). That change was one of the references
Pablo Galindo cited when he proposed the **debug offsets** table ([gh-106597]):
a structure at the start of the runtime state that tells external tools where to
find the data they need, without copying any headers. I later added more fields
to it ([gh-121311]). The debug offsets table is the foundation that PEP 768's
remote debugging interface is built on, and that Tachyon uses to read the
interpreter's state.

So the profiler that now ships with CPython is, in a sense, the result of years
of external tools proving that out-of-process sampling works. CPython made it a
supported use case, and the core developers have now built a sampling profiler
into the interpreter itself. I find that very satisfying, and it's good news
for every external tool too, Austin included.

[bpo-43879]: https://github.com/python/cpython/issues/88045
[bpo-43931]: https://github.com/python/cpython/issues/88097
[bpo-44530]: https://github.com/python/cpython/issues/88696
[gh-105271]: https://github.com/python/cpython/pull/105271
[gh-106597]: https://github.com/python/cpython/issues/106597
[gh-121311]: https://github.com/python/cpython/pull/121311


# Tachyon: A Profiler in the Standard Library

The biggest news of the year is that CPython 3.15 includes a sampling profiler,
`profiling.sampling`, also known as **Tachyon** (it was proposed alongside
reorganising `cProfile` into `profiling.tracing`, in PEP 799). It builds on the
remote debugging support added in 3.14 by PEP 768.

```console
python -m profiling.sampling run --flamegraph script.py
python -m profiling.sampling attach 12345
python -m profiling.sampling run --live script.py
```

Tachyon covers a lot of ground for a first release:

- `run` a script, `attach` to a running process, or `dump` its current stacks.
- Wall time, CPU time, GIL-holding and exception sampling modes.
- An `--async-aware` mode that rebuilds stacks per `asyncio` task.
- A live, `top`-style terminal view.
- Many output formats: pstats, collapsed stacks, interactive HTML flame graphs
  and line-level heatmaps, differential flame graphs, the Firefox Profiler's
  Gecko format, JSONL, and a compact binary format.
- Subprocess profiling, and a default sampling rate of 1 kHz that can be raised.

The obvious advantage is that it's already there: nothing to install, and it's
maintained alongside the interpreter, so it stays in step with internal changes.

The main limit is version coverage. Tachyon only profiles Python 3.15 and later,
and the profiler and the target must run the same minor version (and the same
build type: free-threaded or standard). If your services run on 3.12, Tachyon
doesn't help you yet. Its `--native` option adds placeholder `<native>` frames
to show where Python calls into native code, but doesn't unwind the native
stack itself.

## A Familiar Design

If you've used Austin, much of Tachyon will feel familiar. The basic approach of
reading the interpreter's memory from outside the process is shared with py-spy,
and goes back to pyflame in 2016. But beyond that, many of
the features Tachyon has added since its first commit in August 2025 are ones
Austin has had for years:

| Feature | In Austin since | In Tachyon since |
|---|---|---|
| Separate wall time and CPU time modes | 0.2 (2018) | September 2025 |
| Profiling child processes | 1.0 (2019) | December 2025 |
| Marking samples taken during garbage collection | 3.1 (2021) | November 2025 |
| Writing raw samples to a compact binary format, analysed later | 3.4 (2022) | December 2025 |
| Column-level source locations in that format | 3.5 (2023) | December 2025 |
| Sampling all sub-interpreters | 3.6 (2023) | September 2025 |

Some of these exist in py-spy too, and it goes the other way as well: Tachyon's
`asyncio` support landed before Austin's. That's how open source should work,
with good ideas spreading between projects. What's missing is the credit. PEP
799 doesn't mention Austin, py-spy or any of the external profilers whose
approach Tachyon adopts. I think that's a missed opportunity to recognise the
years of community work that came before the standard library caught up, and
that made it possible.


# py-spy: The Established Choice

[py-spy](https://github.com/benfred/py-spy), written in Rust, made out-of-process
sampling mainstream for Python, and it's what many people mean when they say
"Python sampling profiler".

```console
py-spy record -o profile.svg --pid 12345
py-spy top --pid 12345
py-spy dump --pid 12345
```

Its `record`, `top` and `dump` commands are a model of a simple interface. It
writes SVG flame graphs, Speedscope and Chrome trace files, can follow
subprocesses, filter to threads holding the GIL, and include or exclude idle
threads. With `--native` it also unwinds native C, C++ and Rust frames on Linux
(x86_64 and, since recently, aarch64) and Windows.

py-spy 0.4.2, released in April 2026, added Python 3.14 support. At the time of
writing, free-threaded builds aren't supported yet (there's an open issue
tracking it), and there's no task-aware `asyncio` mode: coroutines appear as
ordinary frames on whichever thread runs the event loop.


# Scalene: The In-Process All-Rounder

[Scalene](https://github.com/plasma-umass/scalene) takes a different approach.
It runs your program for you and profiles from the inside, which lets it measure
things external tools can't easily see.

```console
scalene run script.py
```

Its strengths are breadth and line-level detail:

- CPU time split into Python, native and system time, per line and per
  function.
- Memory profiling through its own allocator, including per-line allocation,
  likely leaks, and copy volume (for example, data accidentally copied between
  NumPy and Python objects).
- GPU time on NVIDIA GPUs, and on Apple GPUs when using PyTorch's MPS backend.
- Wall-clock `await` time per line for `async` code, along with how many
  coroutines were waiting there at once.
- Combined Python and native stacks, shown as flame charts and a timeline.
- AI-generated optimisation suggestions from the web UI, using a provider of
  your choice (OpenAI, Bedrock, Azure or a local model through Ollama).

Two of these numbers come with caveats. Scalene doesn't observe native code
directly: it uses a timer signal, and treats any delay in handling it as time
spent in native code, during which Python can't handle signals. But CPython
only handles signals on the main thread, so in a program with several busy
threads the delay can simply come from waiting for its turn on the GIL. In 2022,
Pablo Galindo showed a multi-threaded, pure-Python program that Scalene reported
as spending most of its time in native code ([scalene#428]). Scalene's author
replied that worker threads are profiled in a different way, but the issue is
still open, and the current code still estimates the main thread's native time
from the signal delay. So treat the Python/native split with some care in
multi-threaded programs.

For GPU time on NVIDIA, Scalene needs the GPU's per-process accounting mode,
which has to be enabled once with root privileges. Without it, Scalene falls
back to the utilisation of the whole GPU, including other processes, and shows
a warning saying so.

Scalene 2.4 (October 2026) supports free-threaded Python 3.13 and 3.14. By its
own figures, the overhead is typically 10–20%. That's fine during development,
but the trade-off of being in-process is that you can't attach Scalene to
something already running. You have to start the program under it.


# Austin: Sampling from the Outside, at Speed

[Austin](https://github.com/P403n1x87/austin) is the tool I maintain. It's a
frame stack sampler written in pure C, with no dependencies beyond the C
standard library and the operating system. It reads the interpreter's memory
from outside the process, writes every sample to a compact binary format called
MOJO, and leaves the analysis to other tools. Because it doesn't aggregate
anything while it samples, it can sample very fast.

```console
austin -o profile.mojo python script.py
sudo austin -p 12345 -o profile.mojo
austin -w 12345   # print the current stacks of every thread
```

Austin 4.1 supports CPython 3.10 through 3.15, including free-threaded builds,
on Linux, macOS and Windows. On Linux it also runs on less common architectures
like i686, armv7 and ppc64le. Each release drops the oldest Python versions, but
older releases of Austin are still available if you need to profile something
older: Austin 4.0 supports 3.9 through 3.14, 3.7 supports 3.8 through 3.13, and
3.5 goes all the way back to Python 2.3.

Austin 4.1 adds four things worth covering in some detail.

## 1. Higher Sampling Rates

Austin 4.0 already more than doubled the maximum sampling rate of the previous
release, by cutting down how much memory Austin reads from the target and how
much work it does to write each sample. 4.1 goes further: Austin now detects
when a thread's stack hasn't changed since the previous sample. When that
happens, it skips walking the stack again and writes a short "same as before"
marker instead of the whole stack, which also makes the output files smaller.
It also buffers its output instead of writing each sample separately.

Every performance change to Austin is benchmarked in CI against the code it
replaces, and the results are posted on the pull request. Here are the two that
made the biggest difference, measured on Linux (x86_64) with Python 3.13, at
the smallest sampling interval (1 µs), where Austin samples as fast as it can:

| Change | Maximum sampling rate (wall time) | Time per sample |
|---|---|---|
| 4.0 performance work, compared with Austin 3.7 ([#295][pr-295]) | 54,000 → 111,000 samples/s (×2.1) | 32.4 → 12.4 µs |
| 4.1 repeated stack detection ([#402][pr-402]) | 121,000 → 166,000 samples/s (+37%) | 15.0 → 10.4 µs |

In CPU time mode, where Austin also has to check whether each thread is on the
CPU, the same changes took the maximum rate from 20,000 to 32,000 samples per
second (+60%) and from 34,000 to 37,000 (+9%) respectively.

Something to keep in mind is that the gain from repeated stack detection depends
on how often stacks repeat between samples. That happens a lot when a program
spends time in long-running loops or calls, but it varies with the workload.

[pr-295]: https://github.com/P403n1x87/austin/pull/295#issuecomment-3168126096
[pr-402]: https://github.com/P403n1x87/austin/pull/402#issuecomment-4350906929

As explained earlier, this matters for accuracy: at the default 100 µs
interval, Austin collects up to 10,000 samples per second per thread, ten times
Tachyon's default rate.

## 2. Native Mode

With `-n/--native`, Austin collects native call stacks and interleaves them with
the Python frames they belong to:

```console
austin -n -i 1ms -o profile.mojo python script.py
```

This shows, for example, what's actually happening inside NumPy, a Cython module
or a Rust extension built with PyO3, not just that time was spent "somewhere in
native code". In native mode Austin also samples threads that never run Python
code, like worker threads started by native libraries, which are invisible to
profilers that only look at Python threads.

Austin users may remember that native stacks used to need a separate tool,
`austinp`, a variant of Austin that uses libunwind to walk native stacks. It was
a separate tool for two reasons. It only worked on Linux. And it broke one of
Austin's founding principles, minimal impact on the program being profiled: to
walk a thread's native stack reliably, libunwind needs the thread to stand
still, so `austinp` had to stop each thread while sampling it. I wrote about
that trade-off in [Spy on Python down to the Linux kernel level][austinp-post].

The new native mode fixes the first problem. It works on Linux (x86_64 and
aarch64), macOS and Windows (x86_64), with no extra dependencies, because Austin
now walks native stacks itself instead of relying on libunwind. Its design owes
a lot to [samply](https://github.com/mstange/samply), Markus Stange's excellent
native sampling profiler, which showed how fast and portable this kind of
unwinding can be. On macOS, Austin captures native stacks the same way samply
does. On Linux, both unwind using the compiler-generated unwind tables, though
they capture stacks differently, and on Windows samply relies on the system's
event tracing while Austin unwinds stacks itself. As far as I know, Austin is
currently the only out-of-process *Python* profiler that unwinds native stacks
on macOS. `austinp` is still available on Linux, for the architectures that
native mode doesn't cover yet and for sampling kernel stacks.

There is one other way to get Python and native frames in the same profile.
Since 3.12, CPython can make Python function calls visible to native profilers
like `perf` and samply (on macOS from Python 3.15), if you enable its [perf
support][perf-support] with `-X perf` or `PYTHONPERFSUPPORT=1`. You get Python
function names in a fully native profile. But it has to be enabled inside the
target process, it only goes down to functions, not lines, and it slows Python
down: in 2023 Mark Shannon [measured][perf-overhead] an 8% slowdown on a
standard build, with more expected in builds that keep frame pointers. So it's a
good option for a quick look at a local program, rather than for attaching to
something already running.

The second problem is a deliberate compromise. To get a consistent native stack,
Austin still has to briefly suspend each thread while sampling it, so native
mode has more impact on the program than Austin's normal mode, and the impact
grows with the sampling rate. Use a larger interval (1 ms is a good start), and
avoid it in production. That's why native mode is an option you turn on, not
the default. In its normal mode, Austin still never pauses the program it's
profiling, and I explained the reasoning behind that in [an earlier
post][accuracy-post].

## 3. asyncio Profiling

On CPython 3.14 and later, Austin tracks the `asyncio` task graph: each event
loop's tasks, the coroutine chain each task is executing or suspended at, and
which tasks are awaiting which. Samples are attributed to the task running on
the thread, and the stacks of suspended tasks are recorded together with the
await relationships between them.

That's what you need to answer the question that ordinary flame graphs get
wrong for async code: not "which frames were on the CPU", but "which *task*
was slow, and was it slow because it was working or because it was waiting on
something else?" And `austin -w` prints the live task tree of a running
application, grouped under the thread whose event loop owns it.

There's a further difference that's easy to miss. Most sampling profilers only
record *what* was running, so each sample is anonymous: they can tell you that
`fetch_user` took 30% of the time, but not whether that was one slow task or a
thousand quick ones. Tachyon's async-aware mode labels each stack with the name
of its task, but still adds the samples up into a single aggregate profile.
Austin records *which* task each sample belongs to, and follows each task from
the first time it sees it to the last. That makes its asyncio support closer to
a tracer in spirit, while keeping the low overhead of sampling.

The [VS Code extension] makes use of this. Alongside the usual flame graph,
which adds up time across all tasks, its Task Trace panel shows a flame chart
for each event loop: every task drawn from when it was first seen to when it
was last seen, nested under the task awaiting it, with how much of that time it
spent running and how much waiting. So you can see what happened over time,
not just where the time went in total, which is often what you need to work out
why a request was slow.


## 4. Making Profiling Approachable

Here's an uncomfortable truth: most Python code never gets profiled. Not because
the tools are missing, but because profiling feels hard to get into. You have to
pick a tool, run it the right way, and then make sense of a flame graph full of
frames you've never heard of. Many developers try it once, feel lost, and go
back to guessing. That's a shame, because as I argued in [How to bust Python
performance issues][bust-perf-issues], a single profiling run often turns up
easy wins. A big part of what I want Austin to do is lower that barrier, and
4.1 approaches it from two directions.

**Let an agent do the work.** Coding agents can now profile code with Austin and
reason about the results themselves. You ask "why is this endpoint slow?", and
the agent runs Austin, finds the hot path, proposes a fix, and profiles again to
check that the fix worked. There are two ways to set this up:

- The [VS Code extension] includes an **MCP server** that exposes the loaded
  profile to agents. Its data tools let the agent ask for the hottest
  functions, call stacks, `asyncio` task traces, GC activity and metadata. It
  works with GitHub Copilot's agent mode with no setup, and with Claude Code,
  Cursor or any other MCP client after running a single command.
- The [austin-python] package has a **query API** that answers the same
  questions in plain Python, and a command-line front-end for it,
  `austin-query`, that prints the results as text tables or JSON. Any agent
  that can run shell commands can use it, in a terminal, a script or CI.
  Pointing the agent at `austin-query --help` is usually all the setup it needs.

The command line is a good place to start, but agents get more out of the
[Python API][query-api] behind it. Each query returns typed objects rather than
text, so the agent can write a short script that hands them over to other
libraries: pandas to compare two profiles, a plotting library to chart the
results, or the project's own code to work out which component owns each hot
function. An analysis that would take a long chain of CLI calls, each one
reading the profile again, becomes a few lines of Python over a profile loaded
once. The selectors and filters are the same as on the command line, e.g.
`q.filter(thread="main").callers("db.py:execute")`, so the agent can move from
one to the other without learning anything new. For example, this is all it
takes to see which functions got faster, or slower, after a fix:

```python
import pandas as pd
from austin.query import ProfileQuery

def hot(path):
    return pd.Series({
        f"{e.location.filename}:{e.location.function}": e.own_pct
        for e in ProfileQuery.from_file(path).top(50)
    })

change = hot("after.mojo").sub(hot("before.mojo"), fill_value=0)
print(change.sort_values().to_string())
```

A word of caution, though: a single pair of profiles is a shaky basis for a
verdict. Sampling, and the system itself, add noise from one run to the next,
so part of the change above could be nothing more than that. For a rigorous
answer, [pyrometry] is a small library of mine that implements the ideas of
[On the Algebraic Properties of Flame Graphs][flamegraph-algebra]. It treats
flame graphs as vectors that can be added, subtracted and averaged, and it
compares two *sets* of profiles, say five runs before a change and five after,
with a statistical test (Hotelling's T²), keeping only the stacks whose
difference is significant. The result is then split into the stacks that
appeared, disappeared, grew or shrank. That's out of reach for a chain of CLI
calls, but it's a short script for an agent with the Python API, and pointing
it at pyrometry gives it a sound method to follow instead of eyeballing two
flame graphs. Nor is this just theory: Austin's own CI uses the same test to
validate every pull request. It profiles the same scenarios ten times with the
base branch and ten times with the changes, on every supported version of
Python, and checks that the new build still reports the same data as the old
one.

**Or let it teach you.** Having an agent fix things for you is useful, but it
doesn't make you any better at reading a profile. So the MCP server also has
action tools that let the agent search and zoom the flame graph in the editor,
while you watch. That turns the extension into a learning tool: instead of
"fix this", you can ask your agent to *walk you through* the analysis. It can
zoom into the hot path and explain why it's hot, point out the frame where your
code hands over to a library, or show you what time spent waiting looks like
compared with time spent computing. You're both looking at the same flame
graph, so after a few sessions you start to recognise the patterns yourself,
and the next time, you might not need to ask. [Busting performance issues, AI
edition][ai-edition] shows both approaches on a real project, including one of
these guided tours.

<!-- TODO: embed demo video / GIF of the agent loop here, ideally one showing
     the agent guiding the user through the flame graph. -->

## Other Things in 4.1

The rest of the release is about meeting Python where it's going, and where it
actually runs. Austin 4.1 supports Python 3.15 on day one, and free-threaded
builds too. Free-threading changes a lot for a profiler: without the GIL,
threads really do run at the same time, so a sampler has to keep up with all of
them at once. The one thing it costs is some accuracy in memory mode, since
without the GIL there's no reliable way to tell which thread caused a change in
memory usage (see below).

Profiles are also easier to read. Threads now show up under the names you gave
them in the `threading` module, so you see `MainThread` and `worker-3` rather
than a list of opaque thread IDs, which makes a big difference in a busy
multi-threaded application.

Finally, a lot of Python runs in containers, and profiling it from the host used
to be awkward. Austin 4.1 handles containerised processes better, and it now
records the target's working directory, virtual environment and `PYTHONPATH`
alongside the samples. That's the information a tool needs to map the file
paths in a profile back to the source files on your machine, even when the code
ran somewhere else.

## Where Austin Falls Short

Whilst Austin has a memory mode, users must be aware that it isn't an allocation
profiler. Its memory mode measures changes in resident memory (RSS) between
samples: how much physical memory the process is actually using, not how much it
has asked for. These can be very different numbers. If you allocate a 512 MB
array but only write to half of it, the operating system only provides physical
memory for the half you've used, so RSS grows by about 256 MB.

That's exactly the test the [Scalene study][scalene-paper] used to compare
memory profilers: allocate 512 MB, touch between 0% and 100% of it, and check
that the profiler reports 512 MB. Austin mostly reported less, and the study
counted that as inaccurate. But reporting only the memory that was touched is
the correct answer for what Austin measures. The study was asking an allocation
question, and Austin answers a residency question. Both are useful: RSS tells
you what your process really costs the machine, which is what matters when
you're about to run out of memory. But if you want to know which line allocated
what, or hunt for leaks, you want an allocation profiler like Scalene or
[memray](https://github.com/bloomberg/memray).
Austin also has no line-level GUI of its own. It relies on the VS Code
extension, the TUI, Speedscope or pprof for visualisation, so out of the box it
asks a bit more of you than Scalene or py-spy do. And attaching to a process
needs elevated privileges on Linux and macOS, as it does for any out-of-process
profiler.


# Which One Should You Use?

There isn't one best profiler. Here's how I'd choose:

- **You're on Python 3.15 and want something quick:** start with Tachyon. It's
  already installed, and it's good.
- **You need to know about memory or GPU time, line by line:** use Scalene, as
  long as you can start the program under it.
- **You need to profile older Python versions, or attach to production:** py-spy
  and Austin both do this well. Austin covers 3.15 and free-threaded builds
  today, and samples faster.
- **You're profiling asyncio code:** on 3.14+, Austin gives you task-level
  profiles that account for waiting time, Tachyon gives you task-aware stacks
  on 3.15, and Scalene tells you which `await` lines are slow.
- **You're working on native extensions, especially on macOS:** use Austin's
  native mode.
- **You want your coding agent to do the profiling, or to teach you how:** use
  Austin's MCP server or `austin-query`.

Other tools worth knowing about: [pyinstrument](https://github.com/joerick/pyinstrument)
for a friendly in-process call tree, [memray](https://github.com/bloomberg/memray)
for serious memory work, and `cProfile` (now `profiling.tracing`) when you need
exact call counts.


# What's Next

Python profiling has never been in better shape. Having a sampling profiler in
the standard library raises the baseline for everyone, and the remote debugging
work in 3.14 and 3.15 makes all external tools more reliable. I expect the next
round of progress to come from two directions: better support for concurrency
(free-threading and `asyncio` together), and making profiling accessible to
everyone, whether that means an agent doing the work or an agent teaching you to
do it yourself. The best profiler is the one people actually use.

Austin 4.1 is available on [PyPI](https://pypi.org/project/austin-dist/),
Homebrew, Snap, Chocolatey, Scoop, conda-forge and as standalone binaries from
[GitHub releases](https://github.com/P403n1x87/austin/releases). The
[documentation](https://p403n1x87.github.io/austin/) covers everything above in
more detail. If you try it, I'd love to hear how it goes.

[VS Code extension]: https://marketplace.visualstudio.com/items?itemName=p403n1x87.austin-vscode
[austin-python]: https://github.com/P403n1x87/austin-python
[query-api]: https://austin-python.readthedocs.io/en/latest/query.html
[pyrometry]: https://github.com/P403n1x87/pyrometry
[flamegraph-algebra]: https://arxiv.org/abs/2301.08941
[deterministic-statistical]: {filename}2019-05-05-python-profiling.md
[austinp-post]: {filename}2021-09-27-python-kernel.md
[accuracy-post]: {filename}2021-12-17-austin-accuracy.md
[bust-perf-issues]: {filename}2021-06-22-bust-perf-issues.md
[ai-edition]: {filename}2026-05-13-bust-perf-issues-ai-ed.md
[scalene-paper]: https://arxiv.org/abs/2212.07597
[scalene#428]: https://github.com/plasma-umass/scalene/issues/428
[perf-support]: https://docs.python.org/3/howto/perf_profiling.html
[perf-overhead]: https://discuss.python.org/t/the-performance-of-python-with-perf-support-is-not-great-and-is-going-to-get-a-lot-worse/25280
