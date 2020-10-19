import asyncio
import aiohttp
import aiokafka
import time
import json
import re

HEADERS = {
	'User-Agent': 'webmonitor/0.1',
}

def json_serialize(value):
	return json.dumps(value).encode('utf-8')

async def fetch_url(config, url):
	# Create a new session for each request, so that all timings include connection establishment
	async with aiohttp.ClientSession(headers=HEADERS, timeout=config.HTTP_TIMEOUT) as session:
		start_time = time.time()
		async with session.get(url) as resp:
			await resp.read()
			resp_time = time.time() - start_time
			return resp_time, resp

async def check_url(config, producer, url, pattern=None):
	timestamp_ms = time.time() * 1000

	try:
		resp_time, resp = await fetch_url(config, url)
	except aiohttp.ClientConnectorError as e:
		result = {'url': url, 'error': repr(e.os_error)}
	except aiohttp.ClientError as e:
		result = {'url': url, 'error': repr(e)}
	except asyncio.TimeoutError as e:
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

async def main(config):
	producer = aiokafka.AIOKafkaProducer(
		value_serializer=json_serialize,
		**config.KAFKA_OPTS
	)

	await producer.start()
	try:
		while True:
			for url, pattern in config.URLS:
				asyncio.create_task(check_url(config, producer, url, pattern))
			await asyncio.sleep(config.CHECK_FREQUENCY)
	finally:
		await producer.stop()

if __name__ == '__main__':
	import importlib.util
	import sys, os

	if len(sys.argv) != 2:
		print('usage: %s CONFIG_PATH' % os.path.basename(sys.argv[0]))
		sys.exit(2)

	try:
		# https://stackoverflow.com/a/67692
		spec = importlib.util.spec_from_file_location('config', sys.argv[1])
		config = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(config)
	except:
		print('Error: Configuration file could not be loaded!', file=sys.stderr)
		raise

	asyncio.run(main(config))

