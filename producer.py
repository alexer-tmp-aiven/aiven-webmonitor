import asyncio
import aiohttp
import aiokafka
import time
import json
import re
from config import KAFKA_OPTS

TIMEOUT = aiohttp.ClientTimeout(total=10)
HEADERS = {
	'User-Agent': 'webmonitor/0.1',
}

def json_serialize(value):
	return json.dumps(value).encode('utf-8')

async def fetch_url(url):
	# Create a new session for each request, so that all timings include connection establishment
	async with aiohttp.ClientSession(headers=HEADERS, timeout=TIMEOUT) as session:
		start_time = time.time()
		async with session.get(url) as resp:
			await resp.read()
			resp_time = time.time() - start_time
			return resp_time, resp

async def check_url(producer, url, pattern=None):
	timestamp_ms = time.time() * 1000

	try:
		resp_time, resp = await fetch_url(url)
	except aiohttp.ClientConnectorError as e:
		result = {'url': url, 'error': repr(e.os_error)}
	except aiohttp.ClientError as e:
		result = {'url': url, 'error': repr(e)}
	else:
		matched = None
		if pattern is not None:
			content = await resp.text()
			matched = bool(re.search(pattern, content))

		result = {
			'url': url,
			'response_time': resp_time,
			'http_status': resp.status,
			'content_ok': matched,
		}

	await producer.send_and_wait(
		'webmonitor',
		result,
		timestamp_ms=timestamp_ms
	)

async def main(urls):
	producer = aiokafka.AIOKafkaProducer(
		value_serializer=json_serialize,
		**KAFKA_OPTS
	)

	await producer.start()
	try:
		while True:
			for url in urls:
				asyncio.create_task(check_url(producer, url, 'utf-8'))
			await asyncio.sleep(1)
	finally:
		await producer.stop()

if __name__ == '__main__':
	import sys

	asyncio.run(main(sys.argv[1:]))

