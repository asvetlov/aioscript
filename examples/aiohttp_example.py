import csv

from aiohttp import ClientSession, web

from aioscript import AbstractScript


class Script(AbstractScript):
    """
    Base usage of AbstractScript: send async requests by means of `aiohttp`.

    This script reads urls from file(source_path) and sends async requests.
    `periodic` method periodically logs info about script progress.

    Run command:
    python3 aiohttp_example.py --source_path=urls.csv --coroutines=10
    """

    def setup(self):
        self.session = ClientSession(loop=self.loop)  # initialize aiohttp client session
        self.total = self.failed = 0  # counter for succeeded and failed requests

    def setup_parser(self):
        parser = super().setup_parser()

        # argument for path to file with urls
        parser.add_argument(
            '--source_path',
            type=str,
            required=True,
        )
        return parser

    async def close(self):
        await self.session.close()

    async def periodic(self):
        """
        Every 15 seconds(by default) script prints progress in console.
        If you want to change the interval,
        run script with different value e.g. `--periodic_interval=42`
        """
        msg = 'Total urls: %(total)s, failed urls: %(failed)s'
        context = {
            'total': self.total,
            'failed': self.failed,
        }
        self.logger.info(msg, context)

    async def handle(self, url):
        """
        Worker sends request to urls simultaneously
        """
        async with self.session.get(url) as response:
            if response.status == web.HTTPOk.status_code:
                self.total += 1
            else:
                self.failed += 1

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
