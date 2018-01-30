import csv

import requests

from aioscript import AbstractScript


class Script(AbstractScript):
    """
    If you have a blocking function(for example, not all db drivers are asynchronous),
    you can run them in a ThreadPoolExecutor not to block event loop.

    Script is a primitive example with synchronous library `requests`.
    Yes, you can send async requests via `aiohttp` client,
    but `requests` is a great option for an example.

    Run command:
    python threading_example.py --source_path=urls.csv --coroutines=5 --threads=5
    """

    def setup_parser(self):
        parser = super().setup_parser()

        # argument for path to file with urls
        parser.add_argument(
            '--source_path',
            type=str,
            required=True,
        )
        return parser

    async def handle(self, url):
        """
        Worker sends request to urls simultaneously
        """
        response = await self.loop.run_in_executor(
            self.executor,
            requests.get,
            url,
        )
        print(url, response.status)

    async def populate(self):
        """
        Open file with urls you want to request
        and populate them to workers.
        """
        with open(self.options.source_path, encoding='utf-8') as fp:
            for row in csv.reader(fp):
                yield row[0]


if __name__ == '__main__':
    Script().run()
