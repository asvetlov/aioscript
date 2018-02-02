import json

from aioscript import AbstractScript


def fib(n):
    if n < 2:
        return n
    return fib(n - 2) + fib(n - 1)


class Script(AbstractScript):
    """
    If you have a CPU-bound task, you can run it via multiprocessing not to block event loop.
    Set class attribute `multiprocessing` to True, pass

    Script that calculates fibonacci(CPU-bound task) numbers on multiple processes
    and dumps results into file when script is done.

    Run command:
    python3 multiprocessing_example.py --output_path=fibonacci.json --coroutines=4 --processes=4
    """

    multiprocessing = True

    def setup(self):
        self.results = {}

    def setup_parser(self):
        parser = super().setup_parser()
        parser.add_argument(
            '--output_path',
            type=str,
            required=True,
        )
        return parser

    async def handle(self, n):
        self.results[n] = await self.run_in_pool(fib, (n, ))

    async def populate(self):
        for n in [30, 32, 35, 38]:
            yield n

    async def done(self):
        with open(self.options.output_path, mode='w') as fp:
            json.dump(self.results, fp)

if __name__ == '__main__':
    Script().run()
