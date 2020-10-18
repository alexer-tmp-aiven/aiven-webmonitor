import asyncio
import aiohttp
import time
import re

TIMEOUT = aiohttp.ClientTimeout(total=10)
HEADERS = {
	'User-Agent': 'webmonitor/0.1',
}

async def fetch_url(url):
	# Create a new session for each request, so that all timings include connection establishment
	async with aiohttp.ClientSession(headers=HEADERS, timeout=TIMEOUT) as session:
		start_time = time.time()
		async with session.get(url) as resp:
			await resp.read()
			resp_time = time.time() - start_time
			return resp_time, resp

async def check_url(url, pattern=None):
	try:
		resp_time, resp = await fetch_url(url)
	except aiohttp.ClientConnectorError as e:
		result = (url, repr(e.os_error))
	except aiohttp.ClientError as e:
		result = (url, repr(e))
	else:
		matched = None
		if pattern is not None:
			content = await resp.text()
			matched = bool(re.search(pattern, content))

		result = (url, resp_time, resp.status, matched)

	print('Done:', result)

async def main(urls):
	while True:
		for url in urls:
			asyncio.create_task(check_url(url, 'utf-8'))
		await asyncio.sleep(1)

if __name__ == '__main__':
	import sys

	asyncio.run(main(sys.argv[1:]))

