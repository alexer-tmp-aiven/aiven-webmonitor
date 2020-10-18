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
		return url, repr(e.os_error)
	except aiohttp.ClientError as e:
		return url, repr(e)

	matched = None
	if pattern is not None:
		content = await resp.text()
		matched = bool(re.search(pattern, content))

	return url, resp_time, resp.status, matched

async def handle_results(tasks):
	for task in tasks:
		print('Done:', await task)

async def main(urls):
	tasks = set()
	while True:
		for url in urls:
			task = asyncio.create_task(check_url(url, 'utf-8'))
			tasks.add(task)
		timeout = asyncio.create_task(asyncio.sleep(1))
		tasks.add(timeout)
		done = set()
		while timeout not in done:
			await handle_results(done)
			done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
		done.remove(timeout)
		await handle_results(done)

if __name__ == '__main__':
	import sys

	asyncio.run(main(sys.argv[1:]))

