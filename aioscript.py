import abc
import argparse
import asyncio
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import aioprocessing


def _sigint(signum, frame):
    os.kill(os.getpid(), signal.SIGINT)


class AbstractScript(metaclass=abc.ABCMeta):

    multiprocessing = False
    pool = None
    periodic_task = None

    def __init__(self):
        parser = self.setup_parser()

        self.options = self.setup_options(
            argv=sys.argv[1:],
            parser=parser,
        )

        self.logger = logging.getLogger('script')

        self.loop = self._setup_loop(use_uvloop=self.options.use_uvloop)

        self.executor = ThreadPoolExecutor(max_workers=self.options.threads)

        self.queue = asyncio.Queue(
            maxsize=self.options.coroutines * 3,
            loop=self.loop,
        )
        self.coroutines = set()

        for _ in range(self.options.coroutines):
            coro = self.loop.create_task(self.coro())
            self.coroutines.add(coro)
            coro.add_done_callback(self.coroutines.remove)

        if self.options.processes > 0:
            self.pool = aioprocessing.AioPool(processes=self.options.processes)

        self.periodic_task = self.loop.create_task(self._periodic())

        self.setup()

    def setup_options(self, argv, parser):
        options = parser.parse_args(argv)

        if self.multiprocessing and not options.processes:
            raise ValueError('--processes >= 1 is required to use pool')

        return options

    def setup_parser(self):
        """
        Defines command-line arguments.
        Base arguments:
        - coroutines - number of workerks.
        - periodic_interval - number of seconds
        :return: argparse.ArgumentParser instance
        """
        parser = argparse.ArgumentParser()

        parser.add_argument(
            '--coroutines',
            default=1,
            type=int,
        )

        parser.add_argument(
            '--threads',
            default=1,
            type=int,
        )

        parser.add_argument(
            '--processes',
            default=0,
            type=int,
        )

        parser.add_argument(
            '--periodic_interval',
            type=int,
            default=15,  # 15 sec
        )

        parser.add_argument(
            '--use_uvloop',
            action='store_true',
        )

        return parser

    def _setup_loop(self, use_uvloop):
        debug = bool(os.environ.get('PYTHONASYNCIODEBUG'))

        if use_uvloop:
            import uvloop
            loop = uvloop.new_event_loop()
        else:
            import asyncio
            loop = asyncio.new_event_loop()

        loop.set_debug(debug)

        return loop

    async def _periodic(self):
        while True:
            try:
                await asyncio.sleep(
                    self.options.periodic_interval,
                    loop=self.loop,
                )

                try:
                    await self.periodic()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.logger.exception(exc, exc_info=exc)
            except asyncio.CancelledError:
                break

    async def periodic(self):
        """
        This task runs every `periodic_interval` seconds.
        `periodic_interval` is 15 seconds by default,
        but can be redefined via console.
        Example: logs number of processed items.
        :return:
        """
        pass

    async def coro(self):
        while True:
            try:
                data = await self.queue.get()

                try:
                    if data is ...:
                        await self.queue.put(data)

                        break

                    await self.handle(data)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.logger.exception(exc, exc_info=exc)
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break

    @abc.abstractmethod
    def setup(self):
        """
        Setup additional dependencies, such as:
        db connection, aiohttp session etc.
        Must be redefined.
        :return:
        """

    @abc.abstractmethod
    def handle(self, data):
        """
        Here must be implemented worker logic
        that processes data accepted from `populate` method.
        Must be redefined.
        :param data: data t
        :return:
        """
        pass

    @abc.abstractmethod
    def populate(self):
        """
        Send data to your workers.
        It can be reading from file, database etc.
        Must be redefined.
        :return:
        """
        pass

    async def done(self):
        """
        Called after all workers are done.
        :return:
        """
        pass

    async def terminated(self):
        """
        Called after script terminating.
        :return:
        """
        pass

    def terminate(self):
        """
        Terminate running script. Kill all workers.
        :return:
        """
        self.loop.call_soon(partial(os.kill, os.getpid(), signal.SIGINT))

        return self.loop.create_future()

    async def _close(self):
        await self.close()

        try:
            self.executor.shutdown(wait=True)
        except BaseException as exc:
            self.logger.exception(exc, exc_info=exc)

    async def close(self):
        pass

    def _finish(self, coro):
        try:
            return self.loop.run_until_complete(coro)
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())

            self.loop.call_soon(self.loop.stop)
            self.loop.run_forever()
            self.loop.close()

    async def run_in_pool(self, func, *args, **kwargs):
        """
        Run CPU-bound calculations in process pool.
        Example:
        ```
        def fibonacci(n):
            if n < 2:
                return n
            return fibonacci(n - 2) + fibonacci(n - 1)

        self.run_in_pool(fibonacci, args=(42, )
        ```
        :param func: heavy function to be run in process pool.
        :param args: args for func.
        :param kwargs: kwargs for func
        :return:
        """
        return await self.pool.coro_apply(func, *args, **kwargs, loop=self.loop)

    async def _run(self):
        try:
            async for item in self.populate():
                await self.queue.put(item)

            await self.queue.join()

            self.queue.put_nowait(...)

            await asyncio.gather(
                *self.coroutines,
                loop=self.loop,
            )

            assert len(self.coroutines) == 0
            assert self.queue.get_nowait() is ...

            await self.done()

            if self.pool is not None:
                self.pool.close()
                self.pool.join()

            msg = 'All done'
            self.logger.info(msg)

            self.loop.call_soon(self.loop.stop)
        except asyncio.CancelledError:
            if self.pool is not None:
                self.pool.terminate()

            for worker in self.coroutines:
                worker.cancel()

            await asyncio.gather(
                *self.coroutines,
                loop=self.loop,
                return_exceptions=True,
            )

            while not self.queue.empty():
                self.queue.get_nowait()
                self.queue.task_done()

            await self.terminated()
        except Exception as exc:
            self.logger.exception(exc, exc_info=exc)
            await self.terminate()

    def run(self):
        """
        Entrypoint to run script.
        Should not be redefined.
        :return:
        """
        signal.signal(signal.SIGTERM, _sigint)
        task = self.loop.create_task(self._run())

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            msg = 'Script is terminated'
            self.logger.warning(msg)

            task.cancel()

            try:
                self.loop.run_until_complete(task)
            except:  # noqa
                pass
        else:
            self.loop.run_until_complete(task)
        finally:
            if self.periodic_task is not None:
                self.periodic_task.cancel()

                try:
                    self.loop.run_until_complete(self.periodic_task)
                except:  # noqa
                    pass

            coro = self._close()

            self._finish(coro)

