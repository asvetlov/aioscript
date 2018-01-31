import asyncio
from unittest import mock

import pytest

from aioscript import AbstractScript


def fib(n):
    if n < 2:
        return n
    return fib(n - 2) + fib(n - 1)


DONE = 42
TERMINATED = 420


def test_script_main():
    check = list()

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            check.append(data)

    cmd_args = ['prog', '--coroutines=5']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert sorted(check) == list(range(5))


def test_script_handle_exception():
    check = list()

    class Script(AbstractScript):
        def setup(self):
            pass

        async def done(self):
            check.append(DONE)

        async def terminated(self):
            check.append(TERMINATED)

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            if data == 3:
                raise ZeroDivisionError

    cmd_args = ['prog', '--coroutines=5']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    # check that Script ends successfully and done method is called
    assert check == [DONE]


def test_script_done():
    check = list()

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            check.append(data)

        async def done(self):
            check.append(DONE)

    cmd_args = ['prog', '--coroutines=5']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert sorted(check) == [0, 1, 2, 3, 4, DONE]


def test_script_done_exception():
    check = list()

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            check.append(data)

        async def done(self):
            1 / 0

        async def terminated(self):
            check.append(TERMINATED)

    cmd_args = ['prog', '--coroutines=5']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert sorted(check) == [0, 1, 2, 3, 4]


def test_script_terminated():
    check = list()

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            if data == 3:
                await self.terminate()

        async def done(self):
            check.append(DONE)

        async def terminated(self):
            check.append(TERMINATED)

    cmd_args = ['prog', '--coroutines=5']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert check == [TERMINATED]


def test_script_terminated_queue_not_empty():
    check = list()

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            for i in range(10):
                yield i

        async def handle(self, data):
            if data == 1:
                await self.terminate()
            await asyncio.sleep(1)

        async def done(self):
            check.append(DONE)

        async def terminated(self):
            check.append(TERMINATED)

    cmd_args = ['prog', '--coroutines=1']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert check == [TERMINATED]


def test_script_periodic():
    check = 0
    sleep_time = 5
    interval = 2

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            yield

        async def handle(self, data):
            await asyncio.sleep(sleep_time)

        async def periodic(self):
            nonlocal check
            check += 1

    periodic_interval = '--periodic_interval={seconds}'.format(
        seconds=interval,
    )
    cmd_args = ['prog', '--coroutines=5', periodic_interval]
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert check == sleep_time // interval


def test_script_periodic_terminate():
    check = list()
    sleep_time = 2
    interval = 1

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            await asyncio.sleep(sleep_time)

        async def periodic(self):
            await self.terminate()

        async def terminated(self):
            check.append(TERMINATED)

    periodic_interval = '--periodic_interval={seconds}'.format(
        seconds=interval,
    )
    cmd_args = ['prog', '--coroutines=5', periodic_interval]
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert check == [TERMINATED]


def test_script_periodic_exception():
    check = list()
    sleep_time = 2
    interval = 1

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            await asyncio.sleep(sleep_time)

        async def periodic(self):
            1 / 0

        async def done(self):
            check.append(DONE)

    periodic_interval = '--periodic_interval={seconds}'.format(
        seconds=interval,
    )
    cmd_args = ['prog', '--coroutines=5', periodic_interval]
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert check == [DONE]


def test_script_run_in_pool():
    check = {}

    class Script(AbstractScript):
        multiprocessing = True

        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, n):
            check[n] = await self.run_in_pool(fib, args=(n, ))

    cmd_args = ['prog', '--coroutines=5', '--processes=2']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    expected = {
        0: 0,
        1: 1,
        2: 1,
        3: 2,
        4: 3,
    }
    assert check == expected


def test_script_run_in_pool_zero_processes():
    check = {}

    class Script(AbstractScript):
        multiprocessing = True

        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, n):
            check[n] = await self.run_in_pool(fib, args=(n, ))

    cmd_args = ['prog', '--coroutines=5', '--processes=0']
    with mock.patch('aioscript.sys.argv', cmd_args):
        with pytest.raises(ValueError):
            Script().run()


def test_script_run_in_pool_terminate():
    check = list()

    class Script(AbstractScript):
        multiprocessing = True

        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            if data == 3:
                await self.terminate()

        async def done(self):
            check.append(DONE)

        async def terminated(self):
            check.append(TERMINATED)

    cmd_args = ['prog', '--coroutines=5', '--processes=4']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert check == [TERMINATED]


def test_script_run_in_executor():
    check = list()

    def blocking_func(n):
        from time import sleep
        sleep(1)
        return n

    class Script(AbstractScript):
        def setup(self):
            pass

        async def populate(self):
            for i in range(5):
                yield i

        async def handle(self, data):
            ret = await self.loop.run_in_executor(
                self.executor,
                blocking_func,
                data,
            )
            check.append(ret)

    cmd_args = ['prog', '--coroutines=5', '--threads=4']
    with mock.patch('aioscript.sys.argv', cmd_args):
        Script().run()

    assert sorted(check) == list(range(5))
