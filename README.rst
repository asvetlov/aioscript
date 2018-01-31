aioscript
=========

:info: Base asyncio script with support of threading and multiprocessing

.. image:: https://travis-ci.org/wikibusiness/aioscript.svg?branch=master
    :target: https://travis-ci.org/wikibusiness/aioscript

.. image:: https://img.shields.io/pypi/v/aioscript.svg
    :target: https://pypi.python.org/pypi/aioscript

.. image:: https://codecov.io/gh/wikibusiness/aioscript/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/wikibusiness/aioscript

Installation
------------

.. code-block:: shell

    pip install aioscript

Usage
-----

.. code-block:: python

    from aiohttp import ClientSession, web

    from aioscript import AbstractScript


    class Script(AbstractScript):

        def setup(self):
            self.session = ClientSession(loop=self.loop)

        async def close(self):
            await self.session.close()

        async def handle(self, url):
            async with self.session.get(url) as response:
                if response.status == web.HTTPOk.status_code:
                    print(response.url, 'Ok')
                else:
                    print(response.url, 'Not ok')

        async def populate(self):
            urls = [
                'https://www.python.org/',
                'https://www.python.org/doc/',
                'https://docs.python.org/3/',
                'https://docs.python.org/3/library/concurrency.html',
                'https://docs.python.org/3/library/asyncio.html',
                'https://docs.python.org/3/library/asyncio-eventloop.html',
            ]
            for url in urls:
                yield url


    if __name__ == '__main__':
        Script().run()

.. code-block:: shell

    python script.py --coroutines=10

Python 3.6+ is required

Thanks
------

The library was donated by `Ocean S.A. <https://ocean.io/>`_

Thanks to the company for contribution.
