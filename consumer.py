import kafka
import psycopg2
import psycopg2.extras
import json
import time
from config import KAFKA_OPTS, PG_DSN

BATCH_SIZE = 10

def json_deserialize(value):
	return json.loads(value.decode('utf-8'))

def main():
	conn = psycopg2.connect(PG_DSN)
	consumer = kafka.KafkaConsumer(
		'webmonitor',
		group_id='webmonitor',
		auto_offset_reset='earliest',
		enable_auto_commit=False,
		value_deserializer=json_deserialize,
		**KAFKA_OPTS
	)

	batch = []
	cur = conn.cursor()
	for msg in consumer:
		if len(batch) >= BATCH_SIZE:
			psycopg2.extras.execute_batch(cur, 'SELECT insert_event(%s, %s, %s, %s, %s, %s, %s)', batch)
			batch = []
			conn.commit()
			consumer.commit()

		timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(msg.timestamp/1000))
		data = msg.value
		ok = 'error' not in data
		batch.append((timestamp, data['url'], ok, data.get('http_status'), data.get('response_time'), data.get('content_ok'), data.get('error')))

if __name__ == '__main__':
	main()

