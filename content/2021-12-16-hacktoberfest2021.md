Title:    How I completed the Hacktoberfest 2021 challenge with a profiler
Authors:  Gabriele N. Tornetta
Date:     2021-12-16 11:56:00 +0100
Category: Programming
Tags:     python, profiling
art:      headings/hacktoberfest.png
pic:      hacktoberfest-2021
Summary:  I shall reveal to you how I managed to complete the Hacktoberfest 2021 challenge with just a profiler. So read on if you are interested!


Remember my post about [how to bust performace issues][bust]? My claim there was
that if you picked a project at random from e.g. GitHub, you'd find something
that would catch your eye if you ran the code through a profiler. Iterating this
process then seemed like a good strategy to generate PRs, which is what you need
to do if you want to [complete the Hacktoberfest challenge][devto] when that
time of the year comes around.

But let's not get the wrong idea. You shouldn't walk away from here thinking
that performance analysis is as trivial as turning the profiler on during test
runs. What my previous post was trying to show is that, in many cases, code is
not profiled and therefore it is easy to find some (rather) low-hanging fruits
that can be fixed easily just as simply as looking at profiling data from the
test suite. Once these are out of the way, that's when the performance analysis
becomes a challenge itself, and some more serious and structured methodologies
are required to make further progress.

So how did I actually use a profiler to complete the Hacktoberfest? I started by
looking at all the Python projects with the `hacktoberfest` topic on GitHub and
picked some that looked interesting to me. The profiler of choice was (surprise,
surprise) [Austin][austin], since it requires no instrumentation and has
practically no impact on the tracee, meaning that I could just sneak a `austin`
in the command line used to start the tests to get the data that I needed.

As a concrete example, let's look at how I was able to detect and fix a
performance regression in [pyWhat][pywhat]. I forked the repository, made a
local clone and looked at how the test suite is run. Peeking at the GitHub
Actions I could see the test suite was triggered with `nox`

    :::shell
    python -m nox

Inside the `noxfile.py` we can find the `tests` session, which is the one we are
interested in

    :::python
    @nox.session
    def tests(session: Session) -> None:
        """Run the test suite."""
        session.run("poetry", "install", "--no-dev", external=True)
        install_with_constraints(
            session,
            "pytest",
            "pytest-black",
            "pytest-cov",
            "pytest-isort",
            "pytest-flake8",
            "pytest-mypy",
            "types-requests",
            "types-orjson",
        )
        session.run("pytest", "-vv", "--cov=./", "--cov-report=xml")

So let's create a `profile` session where we run the test suite through Austin.
All we have to do is add `austin` at the right place in the arguments to
`session.run`, plus some additional options, e.g.:

    :::python
    @nox.session
    def profile(session: Session) -> None:
        """Profile the test suite."""
        session.run("poetry", "install", "--no-dev", external=True)
        profile_file = os.environ.get("AUSTIN_FILE", "tests.austin")
        install_with_constraints(
            session,
            "pytest",
            "pytest-black",
            "pytest-cov",
            "pytest-isort",
            "pytest-flake8",
            "pytest-mypy",
            "types-requests",
            "types-orjson",
        )
        session.run("austin", "-so", profile_file, "-i", "1ms", "pytest")

Here I've actually removed options to `pytest` which I don't care about, like
code coverage, as it's not what I want to profile this time. The `-s` option
tells Austin to give us non-idle samples only, effectively giving us a profile
of CPU time. I'm also allowing the Austin output file to be specified from the
environment via the `AUSTIN_FILE` variable. This means that, if I want to
profile the tests and save the results to `tests.austin`, all I have to do is
invoke

    :::shell
    pipx install nox  # if not installed already
    AUSTIN_FILE=tests.austin nox -rs profile

Once this completes, the profiling data will be sitting in `tests.austin`, ready
to be analysed. With VS Code open on my local copy of `pyWhat`, I've used the
[Austin VS Code][vscode] extension to visualise the data in the form of a flame
graph and, by poking around, this is what caught my eye

<p align="center">
  <a href="https://user-images.githubusercontent.com/20231758/138076258-67c0e621-9055-477f-97f8-5754147267aa.png" target="_blank">
    <img
      src="https://user-images.githubusercontent.com/20231758/138076258-67c0e621-9055-477f-97f8-5754147267aa.png"
      alt="pyWhat tests before the fix"
    />
  </a>
</p>

The suspect here is the chunky `deepcopy` frame stack which is quite noticeable.
The question, of course, is whether the deepcopy is really needed. Clicking on
the `check` frame takes us straight into the part of the code where the
`deepcopy` is triggered. By inspecting the lines around I couldn't really see
the need of making `deepcopy` of objects. So I turned that back (it was
originally a shallow copy, that was later turned into a deep copy) into a
shallow copy with [this PR](https://github.com/bee-san/pyWhat/pull/218/files),
ran the test and checked for the expected output. All was looking find. In fact,
things now looked much, much better! Rerunning the profile session with the
change produced the following picture:

<p align="center">
  <a href="https://user-images.githubusercontent.com/20231758/138076271-6241b43b-d1f3-439d-9afc-3022ce2e231b.png" target="_blank">
    <img
      src="https://user-images.githubusercontent.com/20231758/138076271-6241b43b-d1f3-439d-9afc-3022ce2e231b.png"
      alt="pyWhat tests after the fix"
    />
  </a>
</p>

The `deepcopy` stacks have disappeared and the `check` frame is overall much
slimmer! And so, just like that, a performance regression has been found and
fixed in just a few minutes :).


[austin]: https://github.com/p403n1x87/austin
[bust]: {filename}2021-06-22-bust-perf-issues
[devto]: https://dev.to/p403n1x87
[pywhat]: https://github.com/bee-san/pyWhat
[vscode]: https://marketplace.visualstudio.com/items?itemName=p403n1x87.austin-vscode
