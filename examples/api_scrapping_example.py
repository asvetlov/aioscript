import json

from aiohttp import ClientSession, web

from aioscript import AbstractScript


class Script(AbstractScript):
    """
    Script usage:
    Query some API with different parameters and save results to json file.
    If your API reply with status code 429, that means that your token is exhausted and
    there is no need to continue sending requests. That's why you can terminate all script running
    from `handle` worker by `terminate` method.
    `done` method is called when script ends successfully without terminating.
    'terminated` method is called when script ends by terminating.
    In this case, we need to dump results into file in both cases: success or failure,
    so `terminated` method calls `done` where all results are dumped into file.


    NOTE: As responses stores in RAM memory(`self.results` variable), it may cause memory problems
    when running on huge amounts of data. So you can write data into file at once without storing into memory.

    Run command:
    python3 api_scrapping_example.py --input_path=input.json --output_path=output.json --coroutines=10
    """

    def setup(self):
        self.session = ClientSession(loop=self.loop)  # initialize aiohttp client session
        self.total = 0  # counter for processed requests
        self.results = {}

    def setup_parser(self):
        parser = super().setup_parser()

        parser.add_argument(
            '--input_path',
            type=str,
            required=True,
        )
        parser.add_argument(
            '--output_path',
            type=str,
            required=True,
        )
        parser.add_argument(
            '--api_url',
            type=str,
            required=True,
        )
        return parser

    async def close(self):
        await self.session.close()

    async def periodic(self):
        msg = 'Total requests: %(total)s'
        context = {'total': self.total}
        self.logger.info(msg, context)

    async def done(self):
        with open(self.options.output_path, mode='w', encoding='utf-8') as fp:
            json.dump(self.results, fp)

    async def terminate(self):
        msg = 'Script has stopped because API is banned or manual script terminating'
        self.logger.warning(msg)
        await self.done()

    async def populate(self):
        with open(self.options.input_path, encoding='utf-8') as fp:
            data = json.load(fp)

        for item in data:
            yield item

    async def handle(self, data):
        self.total += 1

        params = {'q': data}  # add params according to your api

        async with self.session.get(
            url=self.options.api_url,
            params=params,
        ) as response:
            if response.status == web.HTTPTooManyRequests.status_code:
                self.terminate()

            self.results[response.url] = await response.json()


if __name__ == '__main__':
    Script().run()
