import abc
import argparse
import asyncio
import logging
import os
import signal
import sys
from functools import partial


class AbstractScript(metaclass=abc.ABCMeta):

    def __init__(self):
        self.loop = asyncio.new_event_loop()

        parser = self.setup_parser()

        self.options = self.setup_options(
            argv=sys.argv[1:],
            parser=parser,
        )

        self.logger = logging.getLogger('script')

        self.queue = asyncio.Queue(
            maxsize=self.options.coroutines * 3,
            loop=self.loop,
        )
        self.coroutines = set()

        for _ in range(self.options.coroutines):
            coro = self.loop.create_task(self.coro())
            self.coroutines.add(coro)
            coro.add_done_callback(self.coroutines.remove)

        self.setup()

    def setup_options(self, argv, parser):
        options = parser.parse_args(argv)

        return options

    def setup_parser(self):
        parser = argparse.ArgumentParser()

        parser.add_argument(
            '--coroutines',
            default=1,
            type=int,
        )

        return parser

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
        :return:
        """

    @abc.abstractmethod
    def handle(self, data):
        """

        :param data:
        :return:
        """
        pass

    @abc.abstractmethod
    def populate(self):
        """
        Send data to your workers.
        It can be reading from file, database etc.
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
        Terminate script running. Kills all workers.
        :return:
        """
        self.loop.call_soon(partial(os.kill, os.getpid(), signal.SIGINT))

        return self.loop.create_future()

    async def _close(self):
        await self.close()

    async def close(self):
        pass

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

            msg = 'All done'
            self.logger.info(msg)

            self.loop.call_soon(self.loop.stop)
        except asyncio.CancelledError:
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
            self.loop.run_until_complete(self._close())
