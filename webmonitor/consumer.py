import kafka
import psycopg2
import psycopg2.extras
import json
import time

def json_deserialize(value):
	return json.loads(value.decode('utf-8'))

def main(config):
	"""Continuously copy events from kafka to postgresql"""
	conn = psycopg2.connect(config.PG_DSN)
	consumer = kafka.KafkaConsumer(
		'webmonitor',
		group_id='webmonitor',
		auto_offset_reset='earliest',
		enable_auto_commit=False,
		value_deserializer=json_deserialize,
		**config.KAFKA_OPTS
	)

	batch = []
	cur = conn.cursor()
	for msg in consumer:
		if len(batch) >= config.BATCH_SIZE:
			psycopg2.extras.execute_batch(cur, 'SELECT insert_event(%s, %s, %s, %s, %s, %s, %s)', batch)
			batch = []
			conn.commit()
			consumer.commit()

		timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(msg.timestamp/1000))
		data = msg.value
		ok = 'error' not in data
		batch.append((timestamp, data['url'], ok, data.get('http_status'), data.get('response_time'), data.get('content_ok'), data.get('error')))

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

	main(config)

