import kafka
import psycopg2
import json
import time
from config import KAFKA_OPTS, PG_DSN

def json_deserialize(value):
	return json.loads(value.decode('utf-8'))

def main():
	conn = psycopg2.connect(PG_DSN)
	consumer = kafka.KafkaConsumer(
		'webmonitor',
		group_id='webmonitor',
		auto_offset_reset='earliest',
		value_deserializer=json_deserialize,
		**KAFKA_OPTS
	)

	cur = conn.cursor()
	for msg in consumer:
		timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(msg.timestamp/1000))
		data = msg.value
		ok = 'error' not in data

		cur.execute('INSERT INTO events (timestamp, url, ok) VALUES (%s, %s, %s) RETURNING id', (timestamp, data['url'], ok))
		event_id = cur.fetchone()[0]

		if ok:
			cur.execute('INSERT INTO results (event_id, http_status, response_time, content_ok) VALUES (%s, %s, %s, %s)', (event_id, data['http_status'], data['response_time'], data['content_ok']))
		else:
			cur.execute('INSERT INTO errors (event_id, error) VALUES (%s, %s)', (event_id, data['error']))

		conn.commit()

if __name__ == '__main__':
	main()

