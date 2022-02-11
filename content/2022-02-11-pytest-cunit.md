Title:    Running C unit tests with pytest
Authors:  Gabriele N. Tornetta
Date:     2022-02-11 14:01:00 +0000
Category: Programming
Tags:     python, testing, c
pic:      pytest-cunit
Summary:  In this post I will describe my approach to C unit testing using pytest as test runner.

[TOC]


# Why?

That's probably what you might be asking right now. Why use a Python testing
framework to test C code? Why don't just use C testing frameworks, like [Google
Test][google-test], or [Check][check]. I can give you an answer with all the
reasons that led me to adopt [pytest][pytest] as the testing framework of choice
for one of my C projects, [Austin][austin]. The first is that I spend most time
coding in Python these days and I have more familiarity with pytest than any
other testing framework. Secondly, whilst Austin is a C project, it actually
targets Python programs, so Python is already one of the testing dependencies
that ends up being installed in CI anyway. Hence, instead of spending time
learning an entire new testing framework, I could quickly write them in Python,
and leverage all the features of pytest, as well as all the packages that are
available for Python, should I ever need to. But these are not all the reasons
for adopting pytest for running C tests. If you keep reading you will discover a
few more that might convince you to use pytest for your C unit tests too!


# Calling native code from Python

Testing C code with Python would only make sense if it was easy to call native
code from the interpreter. Thankfully, the Python standard library comes with
the [`ctypes`][ctypes] module which allows us to do just that! So let's start
looking at some C code, for instance,

    :::c
    # file: fact.c

    long fact(long n) {
        if (n < 1)
            return 1;
        return n * fact(n - 1);
    }

which we want to compile as a shared object, e.g. with

    :::shell
    gcc -shared -o fact.so fact.c

How do we test the `fact` function from Python? Easy peasy!

    :::python
    # file: fact.py

    from ctypes import CDLL

    libfact = CDLL("./fact.so")

    assert libfact.fact(6) == 720
    assert libfact.fact(0) == 1
    assert libfact.fact(-42) == 1

Assuming we are in the directory where both `fact.so` and `fact.py` reside, we
can test the `fact` function inside `fact.c` simply with

    :::shell
    python3 fact.py

If the test succeeds, the script's return code will be 0.

> Congratulations! You have now tested some C code with Python! 🎉


# Enter pytest

We are not here to just play around with bare `assert`s. I promised you the full
power of Python and `pytest`, so clearly we can't settle with just this simple
example. Let's add `pytest` to our test dependencies and do this instead

    :::python
    # file: test_fact.py

    from ctypes import CDLL

    import pytest

    @pytest.fixture
    def libfact():
        yield CDLL("./fact.so")


    def test_fact(libfact):
        assert libfact.fact(6) == 720
        assert libfact.fact(0) == 1
        assert libfact.fact(-42) == 1

Now run `pytest` to get

    :::text
    $ pytest
    =========================== test session starts ============================
    platform linux -- Python 3.10.2, pytest-7.0.0, pluggy-1.0.0
    rootdir: /tmp
    collected 1 item                                                           

    test_fact.py .                                                       [100%]

    ============================ 1 passed in 0.00s =============================

That's some more informative output than what a plain Python test script would
give us! How about starting to leverage some of the other `pytest` features,
like parametrised tests? Let's rewrite our test case like so

    :::python
    # file: test_fact.py

    from ctypes import CDLL

    import pytest


    @pytest.fixture
    def libfact():
        yield CDLL("./fact.so")


    @pytest.mark.parametrize("n,e", [(6, 720), (0, 1), (-42, 1)])
    def test_fact(libfact, n, e):
        assert libfact.fact(n) == e

Let's run this again with `pytest`, this time with a more verbose output:

    :::text
    pytest -vv
    =========================== test session starts ============================
    platform linux -- Python 3.10.2, pytest-7.0.0, pluggy-1.0.0 -- /tmp/.venv/bin/python3.10
    cachedir: .pytest_cache
    rootdir: /tmp
    collected 3 items                                                          

    test_fact.py::test_fact[6-720] PASSED                                [ 33%]
    test_fact.py::test_fact[0-1] PASSED                                  [ 66%]
    test_fact.py::test_fact[-42-1] PASSED                                [100%]

    ============================ 3 passed in 0.01s =============================

Sweet! 🍯


# In the wild

Thus far we've got an idea of how to invoke C from Python and how to write some
simple tests that we can run with `pytest` while also leveraging features like
fixtures and parametrised tests. Let us now step this up a notch and consider
the organisation of sources within an _actual_ C project, for instance

    :::text
    my-c-project/
    ├── docs/
    ├── src/    <- All *.c and *.h sources, perhaps organised into sub-folders
    ├── tests/  <- Our test sources, obviously!
    ├── ChangeLog
    ├── configure.ac
    ├── LICENCE
    ├── Makefile.am
    ├── README
    ...

In the previous example we built the shared object `fact.so` by hand, but in a
CI environment we would probably want to automate that step too. What should we
use for that? A bash script? A makefile? Python, of course! What else?!? 😀

Let's make our sample C sources slightly more interesting. For example, we could
borrow a few parts of the `cache.c` and `cache.h` sources from [Austin][austin],
which implement a simple LRU cache. This is part of the spec

    :::c
    // file: src/cache.h

    #ifndef CACHE_H
    #define CACHE_H

    #include <stdint.h>
    #include <stdlib.h>

    typedef uintptr_t key_dt;
    typedef void *value_t;

    typedef struct queue_item_t
    {
        struct queue_item_t *prev, *next;
        key_dt key;
        value_t value; // Takes ownership of a free-able object
    } queue_item_t;

    typedef struct queue_t
    {
        unsigned count;
        unsigned capacity;
        queue_item_t *front, *rear;
        void (*deallocator)(value_t);
    } queue_t;

    queue_item_t *
    queue_item_new(value_t, key_dt);

    void
    queue_item__destroy(queue_item_t *, void (*)(value_t));

    queue_t *
    queue_new(int, void (*)(value_t));

    int
    queue__is_full(queue_t *);

    int
    queue__is_empty(queue_t *);

    value_t
    queue__dequeue(queue_t *);

    queue_item_t *
    queue__enqueue(queue_t *, value_t, key_dt);

    void
    queue__destroy(queue_t *);

and this is the corresponding part of the implementation

    :::c
    // file: src/cache.c

    #include <stdbool.h>
    #include <stdio.h>

    #include "cache.h"

    #define isvalid(x) ((x) != NULL)

    // ----------------------------------------------------------------------------
    queue_item_t *
    queue_item_new(value_t value, key_dt key)
    {
        queue_item_t *item = (queue_item_t *)calloc(1, sizeof(queue_item_t));

        item->value = value;
        item->key = key;

        return item;
    }

    // ----------------------------------------------------------------------------
    void
    queue_item__destroy(queue_item_t *self, void (*deallocator)(value_t))
    {
        if (!isvalid(self))
            return;

        deallocator(self->value);

        free(self);
    }

    // ----------------------------------------------------------------------------
    queue_t *
    queue_new(int capacity, void (*deallocator)(value_t))
    {
        queue_t *queue = (queue_t *)calloc(1, sizeof(queue_t));

        queue->capacity = capacity;
        queue->deallocator = deallocator;

        return queue;
    }

    // ----------------------------------------------------------------------------
    int
    queue__is_full(queue_t *queue)
    {
        return queue->count == queue->capacity;
    }

    // ----------------------------------------------------------------------------
    int
    queue__is_empty(queue_t *queue)
    {
        return queue->rear == NULL;
    }

    // ----------------------------------------------------------------------------
    value_t
    queue__dequeue(queue_t *queue)
    {
        if (queue__is_empty(queue))
            return NULL;

        if (queue->front == queue->rear)
            queue->front = NULL;

        queue_item_t *temp = queue->rear;
        queue->rear = queue->rear->prev;

        if (queue->rear)
            queue->rear->next = NULL;

        void *value = temp->value;
        free(temp);

        queue->count--;

        return value;
    }

    // ----------------------------------------------------------------------------
    queue_item_t *
    queue__enqueue(queue_t *self, value_t value, key_dt key)
    {
        if (queue__is_full(self))
            return NULL;

        queue_item_t *temp = queue_item_new(value, key);
        temp->next = self->front;

        if (queue__is_empty(self))
            self->rear = self->front = temp;
        else
        {
            self->front->prev = temp;
            self->front = temp;
        }

        self->count++;

        return temp;
    }

    // ----------------------------------------------------------------------------
    void
    queue__destroy(queue_t *self)
    {
        if (!isvalid(self))
            return;

        queue_item_t *next = NULL;
        for (queue_item_t *item = self->front; isvalid(item); item = next)
        {
            next = item->next;
            queue_item__destroy(item, self->deallocator);
        }

        free(self);
    }

It's quite a fair bit of code; however, we are not interested in how the data
structures are implemented, but rather to what it actually implements. This
already gives us plenty to play with.

The important detail here is that our C application has a component impemented
in `cache.c` and we want to unit-test it. Before we can run any actual tests, we
need to build a binary object that we can invoke from Python. So let's put this
code in `tests/cunit/__init__.py`

    :::python
    from pathlib import Path
    from subprocess import PIPE, STDOUT, run

    HERE = Path(__file__).resolve().parent
    TEST = HERE.parent
    ROOT = TEST.parent
    SRC = ROOT / "src"


    class CompilationError(Exception):
        pass


    def compile(source: Path, cflags=[], ldadd=[]):
        binary = source.with_suffix(".so")

        result = run(
            ["gcc", "-shared", *cflags, "-o", str(binary), str(source), *ldadd],
            stdout=PIPE,
            stderr=STDOUT,
            cwd=SRC,
        )

        if result.returncode == 0:
            return

        raise CompilationError(result.stdout.decode())

This simply defines the `compile` utility that allows us to invoke `gcc` to
compile a source and generate the `.so` shared object. We can then use it in our
test source this way

    :::python
    from ctypes import CDLL

    import pytest
    from tests.cunit import SRC, compile

    C = CDLL("libc.so.6")


    @pytest.fixture
    def cache():
        source = SRC / "cache.c"
        compile(source)
        yield CDLL(str(source.with_suffix(".so")))


    def test_cache(cache):
        lru_cache = cache.lru_cache_new(10, C.free)
        assert lru_cache
        cache.lru_cache__destroy(lru_cache)

At this point your project folder should have the following structure

    :::text
    my-c-project/
    ...
    ├── src/
    |   ├── cache.c
    |   └── cache.h
    ├── tests/
    |   ├── cunit/
    |   |   ├── __init__.py
    |   |   └── test_cache.py
    |   └── __init__.py
    ...

and when you run `pytest` again, this time the C source would be compiled at
runtime using `gcc`. The tests then run as before, which should produce the same
output we saw earlier.


# Dead end?

If you're still with me then things are probably looking interesting to you too.
So let's test a bit more of the functions exported by the caching component.
Let's make a test case for the `queue_item_t` and `queue_t` objects, like so

    :::python
    from ctypes import CDLL

    import pytest
    from tests.cunit import SRC, compile

    C = CDLL("libc.so.6")


    @pytest.fixture
    def cache():
        source = SRC / "cache.c"
        compile(source)
        yield CDLL(str(source.with_suffix(".so")))


    NULL = 0


    def test_queue_item(cache):
        value = 1
        queue_item = cache.queue_item_new(value, 42)
        assert queue_item

        cache.queue_item__destroy(queue_item, C.free)


    @pytest.mark.parametrize("qsize", [0, 10, 100, 1000])
    def test_queue(cache, qsize):
        q = cache.queue_new(qsize, C.free)

        assert cache.queue__is_empty(q)
        assert qsize == 0 or not cache.queue__is_full(q)

        assert cache.queue__dequeue(q) is NULL

        values = [C.malloc(16) for _ in range(qsize)]
        assert all(values)

        for k, v in enumerate(values):
            assert cache.queue__enqueue(q, v, k)

        assert qsize == 0 or not cache.queue__is_empty(q)
        assert cache.queue__is_full(q)
        assert cache.queue__enqueue(q, 42, 42) is NULL

        assert values == [cache.queue__dequeue(q) for _ in range(qsize)]

Let's run the new tests with `pytest -vv` and

    :::text
    =============================== test session starts ===============================
    platform linux -- Python 3.10.2, pytest-7.0.0, pluggy-1.0.0 -- /home/gabriele/Projects/cunit/.venv/bin/python3.10
    cachedir: .pytest_cache
    rootdir: /home/gabriele/Projects/cunit
    collected 5 items                                                                 

    tests/cunit/test_cache.py::test_queue_item Fatal Python error: Segmentation fault

    Current thread 0x00007f4016e4f740 (most recent call first):
      File "/home/gabriele/Projects/cunit/tests/cunit/test_cache.py", line 24 in test_queue_item
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/python.py", line 192 in pytest_pyfunc_call
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_callers.py", line 39 in _multicall
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_manager.py", line 80 in _hookexec
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_hooks.py", line 265 in __call__
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/python.py", line 1718 in runtest
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/runner.py", line 168 in pytest_runtest_call
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_callers.py", line 39 in _multicall
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_manager.py", line 80 in _hookexec
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_hooks.py", line 265 in __call__
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/runner.py", line 261 in <lambda>
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/runner.py", line 340 in from_call
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/runner.py", line 260 in call_runtest_hook
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/runner.py", line 221 in call_and_report
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/runner.py", line 132 in runtestprotocol
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/runner.py", line 113 in pytest_runtest_protocol
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_callers.py", line 39 in _multicall
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_manager.py", line 80 in _hookexec
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_hooks.py", line 265 in __call__
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/main.py", line 347 in pytest_runtestloop
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_callers.py", line 39 in _multicall
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_manager.py", line 80 in _hookexec
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_hooks.py", line 265 in __call__
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/main.py", line 322 in _main
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/main.py", line 268 in wrap_session
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/main.py", line 315 in pytest_cmdline_main
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_callers.py", line 39 in _multicall
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_manager.py", line 80 in _hookexec
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/pluggy/_hooks.py", line 265 in __call__
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/config/__init__.py", line 165 in main
      File "/home/gabriele/Projects/cunit/.venv/lib/python3.10/site-packages/_pytest/config/__init__.py", line 188 in console_main
      File "/home/gabriele/Projects/cunit/.venv/bin/pytest", line 8 in <module>
    [1]    337951 segmentation fault  .venv/bin/pytest -vv

Wait, what?! Where are our tests? A segmentation fault?!? Where did that come
from? Well, there goes all this `pytest` hype! 😡

Now, do you think I would have written this post if this was really the end of
the story? 

If you want to figure out for yourself where the problem is, pause here. When
you are ready to carry on, change line 20 to

    :::python
    value = C.malloc(16)

and now the tests will all be happy! However, we really want to avoid crashing
the `pytest` process when we run into a segmentation fault, which is not so rare
when running arbitrary C code. Not only that, but we would like to get some
useful information, like a traceback, that could give us insight as to where the
problem might actually be! One of the many strengths of `pytest` is its
[extensive configuration API][pytest-api]. How do we use it to not crash the
test runner? The idea is to spawn another `pytest` process that runs just _a_
test. Now, if that test causes a segmentation fault, the parent process will
keep running the other tests. Let's put this into `tests/cunit/conftest.py`

    :::python
    # file: tests/cunit/conftest.py

    import os
    import sys
    from subprocess import PIPE, run
    from types import FunctionType


    class SegmentationFault(Exception):
        pass


    class CUnitTestFailure(Exception):
        pass


    def pytest_pycollect_makeitem(collector, name, obj):
        if (
            not os.getenv("PYTEST_CUNIT")
            and isinstance(obj, FunctionType)
            and name.startswith("test_")
        ):
            obj.__cunit__ = (str(collector.fspath), name)


    def cunit(module: str, name: str, full_name: str):
        def _(*_, **__):
            test = f"{module}::{name}"
            env = os.environ.copy()
            env["PYTEST_CUNIT"] = full_name

            result = run([sys.argv[0], "-svv", test], stdout=PIPE, stderr=PIPE, env=env)

            if result.returncode == 0:
                return

            raise CUnitTestFailure("\n" + result.stdout.decode())

        return _


    def pytest_collection_modifyitems(session, config, items) -> None:
        if test_name := os.getenv("PYTEST_CUNIT"):
            # We are inside the sandbox process. We select the only test we care
            items[:] = [_ for _ in items if _.name == test_name]
            return

        for item in items:
            if hasattr(item._obj, "__cunit__"):
                item._obj = cunit(*item._obj.__cunit__, full_name=item.name)

Let's re-run our broken test suite and see what happens this time:

    :::text
    ================================ test session starts =================================
    platform linux -- Python 3.10.2, pytest-7.0.0, pluggy-1.0.0 -- /home/gabriele/Projects/cunit/.venv/bin/python3.10
    cachedir: .pytest_cache
    rootdir: /home/gabriele/Projects/cunit
    collected 5 items                                                                    

    tests/cunit/test_cache.py::test_queue_item <- tests/cunit/conftest.py FAILED   [ 20%]
    tests/cunit/test_cache.py::test_queue[0] <- tests/cunit/conftest.py PASSED     [ 40%]
    tests/cunit/test_cache.py::test_queue[10] <- tests/cunit/conftest.py PASSED    [ 60%]
    tests/cunit/test_cache.py::test_queue[100] <- tests/cunit/conftest.py PASSED   [ 80%]
    tests/cunit/test_cache.py::test_queue[1000] <- tests/cunit/conftest.py PASSED  [100%]

    ====================================== FAILURES ======================================
    __________________________________ test_queue_item ___________________________________

    _ = ()
    __ = {'cache': <CDLL '/home/gabriele/Projects/cunit/src/cache.so', handle 25c8400 at 0x7efd5b5d83d0>}
    test = '/home/gabriele/Projects/cunit/tests/cunit/test_cache.py::test_queue_item'
    env = {'ANDROID_HOME': '/home/gabriele/.android/sdk', 'COLORTERM': 'truecolor', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus', 'DEFAULTS_PATH': '/usr/share/gconf/ubuntu.default.path', ...}
    result = CompletedProcess(args=['.venv/bin/pytest', '-svv', '/home/gabriele/Projects/cunit/tests/cunit/test_cache.py::test_queu...__init__.py", line 188 in console_main\n  File "/home/gabriele/Projects/cunit/.venv/bin/pytest", line 8 in <module>\n')

        def _(*_, **__):
            test = f"{module}::{name}"
            env = os.environ.copy()
            env["PYTEST_CUNIT"] = full_name
        
            result = run([sys.argv[0], "-svv", test], stdout=PIPE, stderr=PIPE, env=env)
        
            if result.returncode == 0:
                return
        
    >       raise CUnitTestFailure("\n" + result.stdout.decode())
    E       tests.cunit.conftest.CUnitTestFailure: 
    E       ============================= test session starts ==============================
    E       platform linux -- Python 3.10.2, pytest-7.0.0, pluggy-1.0.0 -- /home/gabriele/Projects/cunit/.venv/bin/python3.10
    E       cachedir: .pytest_cache
    E       rootdir: /home/gabriele/Projects/cunit
    E       collecting ... collected 1 item
    E       
    E       tests/cunit/test_cache.py::test_queue_item

    tests/cunit/conftest.py:49: CUnitTestFailure
    ============================== short test summary info ===============================
    FAILED tests/cunit/test_cache.py::test_queue_item - tests.cunit.conftest.CUnitTestF...
    ============================ 1 failed, 4 passed in 1.21s =============================

How do we like this better? Now the first test fails with the segmentation
fault, but the rest of the test suite still runs and we can see the reason of
the failure for the first test in the report, i.e. the segmentation fault.

But what is the `conftest.py` code actually doing? Let's have a look. The
`pytest_pycollect_makeitem` hook gets invoked when the tests inside
`tests\cunit` are being collected by `pytest`. At this stage we "mark" them as C
unit tests by giving each collected `item` the `__cunit__` attribute. The value
is a tuple containing the information of where the item came from
(`collection.fspath` is the path of the module that defined the test, e.g.
`tests/cunit/test_cache.py`) and the test name (e.g. `test_queue_item`). In our
case we only care about items that are of `FunctionType` type and that start
with `test_`. The environment variable `PYTEST_CUNIT` is used to detect whether
we are running in the parent `pytest` process or the "sandbox" child. In the
latter case we don't care of marking tests because we know exactly what we want
to run.

Once all the tests have been collected, we use the
`pytest_collection_modifyitems` hook to actually modify the tests that we
previously marked as C unit tests. Again, the behaviour depends on whether we
are in the parent `pytest` process, or in the sandbox. If `PYTEST_CUNIT` is set,
that's the signal that we are in the child `pytest` process. The value, as we
shall see shortly, contains the information needed to pick the test that we want
to run. So we use it to modify the list `items` to just the test that matches
the information stored in `PYTEST_CUNIT`. In the parent `pytest` process we
actually modify what the items that we marked as C unit tests do. Obviously, we
don't want them to run the actual test, but rather a new instance of `pytest`
that will then run the test on behalf of the parent process. The magic happens
inside the "decorator" `cunit`, which we use to build a closure around the test
that we want to run. As you can see, it returns a function (with a bit of a
funny and unusual signature) which, when called, will set the `PYTEST_CUNIT`
variable with the full name of the test (this is to support parametrised tests)
and then run `sys.argv[0]` (which should be `pytest` if we run the test suite
with `pytest`), followed by the switches `-svv` and the path of the module that
provides the test we are wrapping around. This way, when the process terminates,
either because the test passed or something really bad happened, we can inspect
the return code and the streams, and act accordingly.

So now we have a test runner that can handle segmentation faults gracefully, but
still doesn't tell us where they actually happened. Can we get some more
detailed information in the output? When a Python test fails we get a nice
traceback that tells us where things went wrong. Can we do the same with C unit
tests? The answer is **yes**, provided we collect core dumps while tests run. If
you are running on Ubuntu, you can do `ulimit -c unlimited` and a `core` dump
will be generated in the working directory every time a segmentation fault
occurs. We can then run `gdb` in batch mode to print a nice traceback that will
hopefully help us investigate the problem. So let's add these helpers to the
`conftest.py` file

    :::python
    from pathlib import Path
    from subprocess import STDOUT, check_output


    def gdb(cmds: list[str], *args: str) -> str:
        return check_output(
            ["gdb", "-q", "-batch"]
            + [_ for cs in (("-ex", _) for _ in cmds) for _ in cs]
            + list(args),
            stderr=STDOUT,
        ).decode()


    def bt(binary: Path) -> str:
        if Path("core").is_file():
            return gdb(["bt full", "q"], str(binary), "core")
        return "No core dump available."

and improve the `cunit` decorator like so

    :::python
    from tests.cunit import SRC


    def cunit(module: str, name: str, full_name: str):
        def _(*_, **__):
            test = f"{module}::{name}"
            env = os.environ.copy()
            env["PYTEST_CUNIT"] = full_name

            result = run([sys.argv[0], "-svv", test], stdout=PIPE, stderr=PIPE, env=env)

            match result.returncode:
                case 0:
                    return

                case -11:
                    binary_name = Path(module).stem.replace("test_", "")
                    raise SegmentationFault(bt((SRC / binary_name).with_suffix(".so")))

            raise CUnitTestFailure("\n" + result.stdout.decode())

        return _

Now, when we run our broken test suite we should get this more verbose output

    :::text
    ================================ test session starts =================================
    platform linux -- Python 3.10.2, pytest-7.0.0, pluggy-1.0.0 -- /home/gabriele/Projects/cunit/.venv/bin/python3.10
    cachedir: .pytest_cache
    rootdir: /home/gabriele/Projects/cunit
    collected 5 items                                                                    

    tests/cunit/test_cache.py::test_queue_item <- tests/cunit/conftest.py FAILED   [ 20%]
    tests/cunit/test_cache.py::test_queue[0] <- tests/cunit/conftest.py PASSED     [ 40%]
    tests/cunit/test_cache.py::test_queue[10] <- tests/cunit/conftest.py PASSED    [ 60%]
    tests/cunit/test_cache.py::test_queue[100] <- tests/cunit/conftest.py PASSED   [ 80%]
    tests/cunit/test_cache.py::test_queue[1000] <- tests/cunit/conftest.py PASSED  [100%]

    ====================================== FAILURES ======================================
    __________________________________ test_queue_item ___________________________________

    _ = ()
    __ = {'cache': <CDLL '/home/gabriele/Projects/cunit/src/cache.so', handle fc4ba0 at 0x7f5ec8d50460>}
    test = '/home/gabriele/Projects/cunit/tests/cunit/test_cache.py::test_queue_item'
    env = {'ANDROID_HOME': '/home/gabriele/.android/sdk', 'COLORTERM': 'truecolor', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus', 'DEFAULTS_PATH': '/usr/share/gconf/ubuntu.default.path', ...}
    result = CompletedProcess(args=['.venv/bin/pytest', '-svv', '/home/gabriele/Projects/cunit/tests/cunit/test_cache.py::test_queu...__init__.py", line 188 in console_main\n  File "/home/gabriele/Projects/cunit/.venv/bin/pytest", line 8 in <module>\n')
    binary_name = 'cache'

        def _(*_, **__):
            test = f"{module}::{name}"
            env = os.environ.copy()
            env["PYTEST_CUNIT"] = full_name
        
            result = run([sys.argv[0], "-svv", test], stdout=PIPE, stderr=PIPE, env=env)
        
            match result.returncode:
                case 0:
                    return
        
                case -11:
                    binary_name = Path(module).stem.replace("test_", "")
    >               raise SegmentationFault(bt((SRC / binary_name).with_suffix(".so")))
    E               tests.cunit.conftest.SegmentationFault: 
    E               warning: core file may not match specified executable file.
    E               [New LWP 548824]
    E               [Thread debugging using libthread_db enabled]
    E               Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
    E               Core was generated by `/home/gabriele/Projects/cunit/.venv/bin/python3.10 .venv/bin/pytest -svv /home/'.
    E               Program terminated with signal SIGSEGV, Segmentation fault.
    E               #0  raise (sig=<optimised out>) at ../sysdeps/unix/sysv/linux/raise.c:50
    E               50	../sysdeps/unix/sysv/linux/raise.c: No such file or directory.
    E               #0  raise (sig=<optimised out>) at ../sysdeps/unix/sysv/linux/raise.c:50
    E                       set = {
    E                         __val = {[0] = 0, [1] = 1, [2] = 3, [3] = 140049677169600, [4] = 8, [5] = 4714713, [6] = 140049688588951, [7] = 140049678146624, [8] = 3, [9] = 5586517, [10] = 17917168, [11] = 3, [12] = 3, [13] = 140049678074368, [14] = 140049678074368, [15] = 4663610}
    E                       }
    E                       pid = <optimised out>
    E                       tid = <optimised out>
    E                       ret = <optimised out>
    E               #1  <signal handler called>
    E               No locals.
    E               #2  __GI___libc_free (mem=0x1) at malloc.c:3102
    E                       ar_ptr = <optimised out>
    E                       p = <optimised out>
    E                       hook = 0x0
    E               #3  0x00007f5fdbf1b40a in queue_item.destroy () from /home/gabriele/Projects/cunit/src/cache.so
    E               No symbol table info available.
    E               #4  0x00007f5fdb188ff5 in ?? () from /usr/lib/x86_64-linux-gnu/libffi.so.7
    E               No symbol table info available.
    E               #5  0x00007f5fdb18840a in ?? () from /usr/lib/x86_64-linux-gnu/libffi.so.7
    E               No symbol table info available.
    E               #6  0x00007f5fdb1a2286 in ?? () from /usr/lib/python3.10/lib-dynload/_ctypes.cpython-310-x86_64-linux-gnu.so
    E               No symbol table info available.
    E               #7  0x00007f5fdb196eba in ?? () from /usr/lib/python3.10/lib-dynload/_ctypes.cpython-310-x86_64-linux-gnu.so
    E               No symbol table info available.
    E               #8  0x0000000000512f83 in ?? ()
    E               No symbol table info available.
    E               #9  0x00007f5fda9fd160 in ?? ()
    E               No symbol table info available.
    E               #10 0x00007f5fdb1a12d0 in ?? () from /usr/lib/python3.10/lib-dynload/_ctypes.cpython-310-x86_64-linux-gnu.so
    E               No symbol table info available.
    E               #11 0x00007f5fdaa1b658 in ?? ()
    E               No symbol table info available.
    E               #12 0x00007f5fda9f9690 in ?? ()
    E               No symbol table info available.
    E               #13 0x00007f5fdabd1f20 in ?? ()
    E               No symbol table info available.
    E               #14 0x00007f5fdaa1b680 in ?? ()
    E               No symbol table info available.
    E               #15 0x00000000011325a0 in ?? ()
    E               No symbol table info available.
    E               #16 0x00007f5fda9f214a in ?? ()
    E               No symbol table info available.
    E               #17 0x00007f5fdaa1b820 in ?? ()
    E               No symbol table info available.
    E               #18 0x00007f5fda9f20f0 in ?? ()
    E               No symbol table info available.
    E               #19 0x00007f5fda9fd160 in ?? ()
    E               No symbol table info available.
    E               #20 0x000000000057b1ec in ?? ()
    E               No symbol table info available.
    E               #21 0x59586f2afaac8ab6 in ?? ()
    E               No symbol table info available.
    E               #22 0x00007f5fdaa1b7e0 in ?? ()
    E               No symbol table info available.
    E               #23 0x0000000001116534 in ?? ()
    E               No symbol table info available.
    E               #24 0x00007f5fda9d50c0 in ?? ()
    E               No symbol table info available.
    E               #25 0x00007f5fdaa1b808 in ?? ()
    E               No symbol table info available.
    E               #26 0x8000000000000002 in ?? ()
    E               No symbol table info available.
    E               #27 0x00007f5fda949480 in ?? ()
    E               No symbol table info available.
    E               #28 0x00007f5fdaa1b810 in ?? ()
    E               No symbol table info available.
    E               #29 0x00007f5fda96aec0 in ?? ()
    E               No symbol table info available.
    E               #30 0x00007f5fdaa1b800 in ?? ()
    E               No symbol table info available.
    E               #31 0x00000000011164f0 in ?? ()
    E               No symbol table info available.
    E               #32 0x0000000000575f1d in ?? ()
    E               No symbol table info available.
    E               #33 0x42439dfdd749cffb in ?? ()
    E               No symbol table info available.
    E               #34 0x00007f5fdaa1b620 in ?? ()
    E               No symbol table info available.
    E               #35 0x0000000001116534 in ?? ()
    E               No symbol table info available.
    E               #36 0x00007f5fdb4ec070 in ?? ()
    E               No symbol table info available.
    E               #37 0x00007f5fda9fbb80 in ?? ()
    E               No symbol table info available.
    E               #38 0x0000000000000000 in ?? ()
    E               No symbol table info available.

    tests/cunit/conftest.py:56: SegmentationFault
    ============================== short test summary info ===============================
    FAILED tests/cunit/test_cache.py::test_queue_item - tests.cunit.conftest.Segmentati...
    ============================ 1 failed, 4 passed in 1.73s =============================

Hmm Still not that useful. What if we compile with debug symbols? Let's change
the `cache` fixture in `test_cache.py` so that it compiles the caching sources
with the `-g` option

    :::python
    @pytest.fixture
    def cache():
        source = SRC / "cache.c"
        compile(source, cflags=["-g"])
        yield CDLL(str(source.with_suffix(".so")))

Now that's much, _much_ better!

    :::text
    E               #3  0x00007ff51cf8b40a in queue_item__destroy (self=0x104ac60, deallocator=0x7ff51cc68850 <__GI___libc_free>) at /home/gabriele/Projects/cunit/src/cache.c:37

This tells us _exactly_ where the probem occurred. Now that we have this
information we can fix the test and make the test suite happy again! 🎉


# Pythonic C unit testing

OK, running C unit tests is nice and fun, but it doesn't save us much in terms
of typing. In fact, the tests we wrote so far not only feel quite verbose,
considering we are writing Python code, but don't feel Pythonic at all. Whilst
there is, in principle, no reason why non-Python tests written in Python should
look and feel Pythonic, can we somehow do something perhaps more elegant? The
idea of using a fixture to wrap around a binary object is perhaps interesting,
but can we maybe pretend that `cache` is a Python module instead, so that we can
do things like `from cache import queue_item_new` etc... and sweep all this
`ctypes` business under the carpet? Well, let's give this a try, shall we?

Back in `tests/cunit/__init__.py`, let's add the following subtype of
`ModuleType`:

    :::python
    from ctypes import CDLL
    from types import ModuleType


    class CModule(ModuleType):
        def __init__(self, source):
            super().__init__(source.name, f"Generated from {source.with_suffix('.c')}")
            self.__binary__ = CDLL(source.with_suffix(".so"))
            print(self.__binary__.__dict__)

        def __getattr__(self, name):
            return getattr(self.__binary__, name)

        @classmethod
        def compile(cls, source, cflags=[], ldadd=[]):
            compile(source.with_suffix(".c"), cflags, ldadd)
            return cls(source)

Now create `tests/cunit/cache.py` with the following content

    :::python
    import sys
    from pathlib import Path

    from tests.cunit import SRC, CModule

    CFLAGS = ["-g"]

    sys.modules[__name__] = CModule.compile(SRC / Path(__file__).stem, cflags=CFLAGS)

and get rid of the `cache` fixture in `test_cache.py` (make sure to remove it
also from the test arguments!). Instead, add

    :::python
    import tests.cunit.cache as cache

_et voilà_! Now `cache` feels like a Python module that exports ordinary
functions that we can call like any other Python function.

Now, what about this code

    :::python
    def test_queue_item():
        value = C.malloc(16)
        queue_item = cache.queue_item_new(value, 42)
        assert queue_item

        cache.queue_item__destroy(queue_item, C.free)

Clearly `cache.queue_item_new` is creating a new object. The Pythonic way of
writing something like this would be

    :::python
    def test_queue_item():
        value = C.malloc(16)
        queue_item = cache.QueueItem(value, 42)
        assert queue_item

and we don't even care about destroying the object as we'd love the garbage
collector to take care of that for us. That's clearly a more Pythonic way of
going about our C unit tests. Can we achieve something like this? The answer is
once again _yes_, but ... we can make this work provided we make some further
assumption, like some naming conventions. You might have noticed that the data
structures defined in `cache.h` have the naming `<adt>_t`, in a OOP flavour.
Methods follow the naming convention `<adt>_<staticmethod>` and
`<adt>__<emethod>`. Some of the methods have _special_ names, like `<adt>_new`,
`<adt>__destroy` etc.... So, provided we adhere to _some_ naming conventions,
like this one, we could dynamically create Python types at runtime. How? With
the secret art of [metaprogramming][metaprogramming]. But before we can start
creating new types at runtime, we need to be able to parse C header files to
infer their definitions. That's why our next step is to add `pycparser` to our
test dependencies, and implement a C AST visitor that can collect all the
relevant type and method declarations that we can use to build the spec for
Python types. Here is what it might look like

    :::python
    from ctypes import c_char_p

    from pycparser import c_ast, c_parser
    from pycparser.plyparser import ParseError

    class DeclCollector(c_ast.NodeVisitor):
        def __init__(self):
            self.types = {}
            self.functions = []

        def _get_type(self, node):
            print(node)
            return self.types[" ".join(node.type.type.names)]

        def visit_Typedef(self, node):
            if isinstance(node.type.type, c_ast.Struct) and node.type.declname.endswith(
                "_t"
            ):
                struct = node.type.type
                self.types[node.type.declname[:-2]] = CTypeDef(
                    node.type.declname,
                    [decl.name for decl in struct.decls],
                )

        def visit_Decl(self, node):
            if "extern" in node.storage:
                return

            if isinstance(node.type, c_ast.FuncDecl):
                func_name = node.name
                ret_type = node.type.type
                rtype = None
                if isinstance(ret_type, c_ast.PtrDecl):
                    if "".join(ret_type.type.type.names) == "char":
                        rtype = c_char_p
                args = (
                    [_.name if hasattr(_, "name") else None for _ in node.type.args.params]
                    if node.type.args is not None
                    else []
                )
                if func_name.endswith("_new"):
                    self.types[f"{func_name[:-4]}"].constructor = CFunctionDef(
                        "new", args, rtype
                    )
                elif "__" in func_name:
                    type_name, _, method_name = func_name.partition("__")
                    if not type_name:
                        return
                    self.types[type_name].methods.append(
                        CFunctionDef(method_name, args, rtype)
                    )
                else:
                    self.functions.append(CFunctionDef(func_name, args, rtype))

        def collect(self, decl):
            parser = c_parser.CParser()
            try:
                ast = parser.parse(decl, filename="<preprocessed>")
            except ParseError as e:
                lines = decl.splitlines()
                line, col = (
                    int(_) - 1 for _ in e.args[0].partition(" ")[0].split(":")[1:3]
                )
                for i in range(max(0, line - 4), min(line + 5, len(lines))):
                    if i != line:
                        print(f"{i+1:5d}  {lines[i]}")
                    else:
                        print(f"{i+1:5d}  \033[33;1m{lines[line]}\033[0m")
                        print(" " * (col + 5) + "\033[31;1m<<^\033[0m")
                raise

            self.visit(ast)
            return {
                k: v
                for k, v in self.types.items()
                if isinstance(v, CTypeDef) and v.constructor
            }

This is also a handful, but the behaviour is very simple. We define an AST
visitor that listens to `typedef`s and declarations. For the former we single
out structure declarations and we store the relevant information inside an
instance of the custom `CTypeDef` dataclass; as for the latter, we only trap
function declaration (plus a special handling for those functions that return
`char *`). The two intermediate dataclasses `CTypeDef` and `CFunctionDef` are
merely defined as (up to you to use the more elegant `@dataclass` decorator)

    :::python
    class CFunctionDef:
        def __init__(self, name, args, rtype):
            self.name = name
            self.args = args
            self.rtype = rtype


    class CTypeDef:
        def __init__(self, name, fields):
            self.name = name
            self.fields = fields
            self.methods = []
            self.constructor = False

Armed with these definitions we can enhance our `CModule` class like so

    :::python
    class CModule(ModuleType):
        def __init__(self, source):
            super().__init__(source.name, f"Generated from {source.with_suffix('.c')}")
            self.__binary__ = CDLL(source.with_suffix(".so"))

            collector = DeclCollector()

            for name, ctypedef in collector.collect(
                preprocess(source.with_suffix(".h"))
            ).items():
                parts = name.split("_")
                py_name = "".join((_.capitalize() for _ in parts))
                setattr(self, py_name, CMetaType(self, ctypedef, None))

            for cfuncdef in collector.functions:
                name = cfuncdef.name
                try:
                    cfunc = CFunction(cfuncdef, getattr(self.__binary__, name))
                    setattr(self, name, cfunc)
                except AttributeError:
                    # Not part of the binary
                    pass

        @classmethod
        def compile(cls, source, cflags=[], ldadd=[]):
            compile(source.with_suffix(".c"), cflags, ldadd)
            return cls(source)

That is, we add the collected types and functions as attributes to the C module.
This is the C type metaclass that we use as a C type factory

    :::python
    class CMetaType(type(Structure)):
        def __new__(cls, cmodule, ctypedef, _=None):
            ctype = super().__new__(
                cls,
                ctypedef.name,
                (CType,),
                {"__cmodule__": cmodule},
            )

            constructor = getattr(cmodule.__binary__, f"{ctypedef.name[:-2]}_new")
            ctype.new = CStaticMethod(ctypedef.constructor, constructor, ctype)

            for method_def in ctypedef.methods:
                method_name = method_def.name
                method = getattr(cmodule.__binary__, f"{ctypedef.name[:-2]}__{method_name}")
                setattr(ctype, method_name, CMethod(method_def, method, ctype))

            ctype.__cname__ = ctypedef.name

            return ctype

This is responsible for creating a new C type as a Python type, with all the
methods added as appropriate instances of wrappers around the C functions (note
the special handling of the `_new` method!):

    :::python
    class CFunction:
        def __init__(self, cfuncdef, cfunc):
            self.__name__ = cfuncdef.name
            self.__args__ = cfuncdef.args
            self.__cfunc__ = cfunc
            if cfuncdef.rtype is not None:
                self.__cfunc__.restype = cfuncdef.rtype

            self._posonly = all(_ is None for _ in self.__args__)

        def check_args(self, args, kwargs):
            if self._posonly and kwargs:
                raise ValueError(f"{self} takes only positional arguments")

            nargs = len(args) + len(kwargs)
            if nargs != len(self.__args__):
                raise TypeError(
                    f"{self} takes exactly {len(self.__args__)} arguments ({nargs} given)"
                )

        def __call__(self, *args, **kwargs):
            self.check_args(args, kwargs)
            return self.__cfunc__(*args, **kwargs)

        def __repr__(self):
            return f"<CFunction '{self.__name__}'>"


    class CMethod(CFunction):
        def __init__(self, cfuncdef, cfunc, ctype):
            super().__init__(cfuncdef, cfunc)
            self.__ctype__ = ctype

        def __get__(self, obj, objtype=None):
            def _(*args, **kwargs):
                cargs = [obj.__cself__, *args]
                self.check_args(cargs, kwargs)

                return self.__cfunc__(*cargs, **kwargs)

            _.__cmethod__ = self

            return _

        def __repr__(self):
            return f"<CMethod '{self.__name__}' of CType '{self.__ctype__.__name__}'>"


    class CStaticMethod(CFunction):
        def __init__(self, cfuncdef, cfunc, ctype):
            super().__init__(cfuncdef, cfunc)
            self.__ctype__ = ctype

        def __repr__(self):
            return f"<CStaticMethod '{self.__name__}' of CType '{self.__ctype__.__name__}'>"

The `CType` class implementation tries to mimic the behaviour of Python classes,
with `__cself__` playing the role of the C analogue of `self`:

    :::python
    class CType(Structure):
        def __init__(self, *args, **kwargs):
            self.__cself__ = self.new(*args, **kwargs)

        def __del__(self):
            if len(self.destroy.__cmethod__.__args__) == 1:
                self.destroy()

        def __repr__(self):
            return f"<{self.name} CObject at {self.__cself__}>"

We also handle the destructor by overriding the `__del__` special method so that
the garbage collector can take care of freeing memory for us.

In general, we would need to preprocess sources, especially headers, before we
can parse them concretely with `pycparser`. That's why we also need to define
something like

    :::python
    restrict_re = re.compile(r"__restrict \w+")

    _header_head = r"""
    #define __attribute__(x)
    #define __extension__
    #define __inline inline
    #define __asm__(x)
    #define __const=const
    #define __inline__ inline
    #define __inline inline
    #define __restrict
    #define __signed__ signed
    #define __GNUC_VA_LIST
    #define __gnuc_va_list char
    #define __thread
    """


    def preprocess(source: Path) -> str:
        with source.open() as fin:
            code = _header_head + fin.read()
            return restrict_re.sub(
                "",
                run(
                    ["gcc", "-E", "-P", "-"],
                    stdout=PIPE,
                    input=code.encode(),
                    cwd=SRC,
                ).stdout.decode(),
            )

The `_header_head` and the `restrict_re` are needed to take care of GCC
extensions, which are not supported by `pycparser`. But apart from them, all we
do is invoke the `gcc` preprocessor on the C sources. Putting everything
together inside `tests/cunit/__init__.py` we would then have something that
looks like

    :::python
    import ctypes
    import re
    from ctypes import CDLL, POINTER, Structure, c_char_p, cast
    from pathlib import Path
    from subprocess import PIPE, STDOUT, run
    from types import ModuleType
    from typing import Any, Optional

    from pycparser import c_ast, c_parser
    from pycparser.plyparser import ParseError

    HERE = Path(__file__).resolve().parent
    TEST = HERE.parent
    ROOT = TEST.parent
    SRC = ROOT / "src"


    restrict_re = re.compile(r"__restrict \w+")

    _header_head = r"""
    #define __attribute__(x)
    #define __extension__
    #define __inline inline
    #define __asm__(x)
    #define __const=const
    #define __inline__ inline
    #define __inline inline
    #define __restrict
    #define __signed__ signed
    #define __GNUC_VA_LIST
    #define __gnuc_va_list char
    #define __thread
    """


    def preprocess(source: Path) -> str:
        with source.open() as fin:
            code = _header_head + fin.read()
            return restrict_re.sub(
                "",
                run(
                    ["gcc", "-E", "-P", "-"],
                    stdout=PIPE,
                    input=code.encode(),
                    cwd=SRC,
                ).stdout.decode(),
            )


    def compile(source: Path, cflags=[], ldadd=[]):
        binary = source.with_suffix(".so")

        result = run(
            ["gcc", "-shared", *cflags, "-o", str(binary), str(source), *ldadd],
            stdout=PIPE,
            stderr=STDOUT,
            cwd=SRC,
        )

        if result.returncode == 0:
            return

        raise RuntimeError(result.stdout.decode())


    C = CDLL("libc.so.6")


    class CFunctionDef:
        def __init__(self, name, args, rtype):
            self.name = name
            self.args = args
            self.rtype = rtype


    class CTypeDef:
        def __init__(self, name, fields):
            self.name = name
            self.fields = fields
            self.methods = []
            self.constructor = False


    class CType(Structure):
        def __init__(self, *args, **kwargs):
            self.__cself__ = self.new(*args, **kwargs)

        def __del__(self):
            if len(self.destroy.__cmethod__.__args__) == 1:
                self.destroy()

        def __repr__(self):
            return f"<{self.name} CObject at {self.__cself__}>"


    class CFunction:
        def __init__(self, cfuncdef, cfunc):
            self.__name__ = cfuncdef.name
            self.__args__ = cfuncdef.args
            self.__cfunc__ = cfunc
            if cfuncdef.rtype is not None:
                self.__cfunc__.restype = cfuncdef.rtype

            self._posonly = all(_ is None for _ in self.__args__)

        def check_args(self, args, kwargs):
            if self._posonly and kwargs:
                raise ValueError(f"{self} takes only positional arguments")

            nargs = len(args) + len(kwargs)
            if nargs != len(self.__args__):
                raise TypeError(
                    f"{self} takes exactly {len(self.__args__)} arguments ({nargs} given)"
                )

        def __call__(self, *args, **kwargs):
            self.check_args(args, kwargs)
            return self.__cfunc__(*args, **kwargs)

        def __repr__(self):
            return f"<CFunction '{self.__name__}'>"


    class CMethod(CFunction):
        def __init__(self, cfuncdef, cfunc, ctype):
            super().__init__(cfuncdef, cfunc)
            self.__ctype__ = ctype

        def __get__(self, obj, objtype=None):
            def _(*args, **kwargs):
                cargs = [obj.__cself__, *args]
                self.check_args(cargs, kwargs)

                return self.__cfunc__(*cargs, **kwargs)

            _.__cmethod__ = self

            return _

        def __repr__(self):
            return f"<CMethod '{self.__name__}' of CType '{self.__ctype__.__name__}'>"


    class CStaticMethod(CFunction):
        def __init__(self, cfuncdef, cfunc, ctype):
            super().__init__(cfuncdef, cfunc)
            self.__ctype__ = ctype

        def __repr__(self):
            return f"<CStaticMethod '{self.__name__}' of CType '{self.__ctype__.__name__}'>"


    class CMetaType(type(Structure)):
        def __new__(cls, cmodule, ctypedef, _=None):
            ctype = super().__new__(
                cls,
                ctypedef.name,
                (CType,),
                {"__cmodule__": cmodule},
            )

            constructor = getattr(cmodule.__binary__, f"{ctypedef.name[:-2]}_new")
            ctype.new = CStaticMethod(ctypedef.constructor, constructor, ctype)

            for method_def in ctypedef.methods:
                method_name = method_def.name
                method = getattr(cmodule.__binary__, f"{ctypedef.name[:-2]}__{method_name}")
                setattr(ctype, method_name, CMethod(method_def, method, ctype))

            ctype.__cname__ = ctypedef.name

            return ctype


    class DeclCollector(c_ast.NodeVisitor):
        def __init__(self):
            self.types = {}
            self.functions = []

        def _get_type(self, node):
            print(node)
            return self.types[" ".join(node.type.type.names)]

        def visit_Typedef(self, node):
            if isinstance(node.type.type, c_ast.Struct) and node.type.declname.endswith(
                "_t"
            ):
                struct = node.type.type
                self.types[node.type.declname[:-2]] = CTypeDef(
                    node.type.declname,
                    [decl.name for decl in struct.decls],
                )

        def visit_Decl(self, node):
            if "extern" in node.storage:
                return

            if isinstance(node.type, c_ast.FuncDecl):
                func_name = node.name
                ret_type = node.type.type
                rtype = None
                if isinstance(ret_type, c_ast.PtrDecl):
                    if "".join(ret_type.type.type.names) == "char":
                        rtype = c_char_p
                args = (
                    [_.name if hasattr(_, "name") else None for _ in node.type.args.params]
                    if node.type.args is not None
                    else []
                )
                if func_name.endswith("_new"):
                    self.types[f"{func_name[:-4]}"].constructor = CFunctionDef(
                        "new", args, rtype
                    )
                elif "__" in func_name:
                    type_name, _, method_name = func_name.partition("__")
                    if not type_name:
                        return
                    self.types[type_name].methods.append(
                        CFunctionDef(method_name, args, rtype)
                    )
                else:
                    self.functions.append(CFunctionDef(func_name, args, rtype))

        def collect(self, decl):
            parser = c_parser.CParser()
            try:
                ast = parser.parse(decl, filename="<preprocessed>")
            except ParseError as e:
                lines = decl.splitlines()
                line, col = (
                    int(_) - 1 for _ in e.args[0].partition(" ")[0].split(":")[1:3]
                )
                for i in range(max(0, line - 4), min(line + 5, len(lines))):
                    if i != line:
                        print(f"{i+1:5d}  {lines[i]}")
                    else:
                        print(f"{i+1:5d}  \033[33;1m{lines[line]}\033[0m")
                        print(" " * (col + 5) + "\033[31;1m<<^\033[0m")
                raise

            self.visit(ast)
            return {
                k: v
                for k, v in self.types.items()
                if isinstance(v, CTypeDef) and v.constructor
            }


    class CModule(ModuleType):
        def __init__(self, source):
            super().__init__(source.name, f"Generated from {source.with_suffix('.c')}")
            self.__binary__ = CDLL(source.with_suffix(".so"))

            collector = DeclCollector()

            for name, ctypedef in collector.collect(
                preprocess(source.with_suffix(".h"))
            ).items():
                parts = name.split("_")
                py_name = "".join((_.capitalize() for _ in parts))
                setattr(self, py_name, CMetaType(self, ctypedef, None))

            for cfuncdef in collector.functions:
                name = cfuncdef.name
                try:
                    cfunc = CFunction(cfuncdef, getattr(self.__binary__, name))
                    setattr(self, name, cfunc)
                except AttributeError:
                    # Not part of the binary
                    pass

        @classmethod
        def compile(cls, source, cflags=[], ldadd=[]):
            compile(source.with_suffix(".c"), cflags, ldadd)
            return cls(source)

So let's use this new technology to make our C unit tests more _Pythonesque_.
This is what our new `test_cache.py` can look like

    :::python
    import pytest
    from tests.cunit import C
    from tests.cunit.cache import Queue, QueueItem

    NULL = 0


    def test_queue_item():
        value = C.malloc(16)
        queue_item = QueueItem(value, 42)
        assert queue_item.__cself__

        queue_item.destroy(C.free)


    @pytest.mark.parametrize("qsize", [0, 10, 100, 1000])
    def test_queue(qsize):
        q = Queue(qsize, C.free)

        assert q.is_empty()
        assert qsize == 0 or not q.is_full()

        assert q.dequeue() is NULL

        values = [C.malloc(16) for _ in range(qsize)]
        assert all(values)

        for k, v in enumerate(values):
            assert q.enqueue(v, k)

        assert qsize == 0 or not q.is_empty()
        assert q.is_full()
        assert q.enqueue(42, 42) is NULL

        assert values == [q.dequeue() for _ in range(qsize)]

We can practically treat our C binary object as if it were an actual Python
module and import the `Queue` and `QueueItem` types from it. We can then use
them as if they were actual Python classes and call methods on them. How cool is
that? 😄


# Coverage, please!

What about test coverage? If you've used `pytest` before, you are probably
familiar with the `pytest-cov` plugin, which is a handy way of collecting and
reporting test coverage. GCC supports the `-fprofile-arcs` and `-ftest-coverage`
to emit coverage data. So if we also wanted to get test coverage data while
running C unit tests with `pytest`, all we would have to do is add these flags
to the `CFLAGS` list in the `cache.py` module. The [`gcovr`][gcovr] tool is
actually inspired by the Python counterpart `coverage.py` and can be used to
generate some nice reports. In particular, it could be used to generate
Cobertura XML reports that could be uploaded to services like
[codecov.io][codecov].


[austin]: https://github.com/p403n1x87/austin
[check]: https://libcheck.github.io/check/
[codecov]: https://codecov.io/
[ctypes]: https://docs.python.org/3/library/ctypes.html
[gcovr]: https://gcovr.com/en/stable/
[google-test]: https://github.com/google/googletest
[metaprogramming]: https://realpython.com/python-metaclasses/
[pytest]: https://github.com/pytest-dev/pytest/
[pytest-api]: https://docs.pytest.org/en/latest/reference/reference.html
