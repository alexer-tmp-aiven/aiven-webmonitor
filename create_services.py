from aiven.client.cli import AivenCLI
import psycopg2
import socket
import time
import sys, os

def wait_for_dns(name):
	while True:
		try:
			return socket.gethostbyname(name)
		except socket.gaierror:
			time.sleep(10)

if len(sys.argv) != 2:
	print('usage: %s DIRECTORY' % os.path.basename(sys.argv[0]))
	print('Creates the required services and writes the configuration to DIRECTORY.')
	sys.exit(2)

# Read the database schema first
basedir = os.path.dirname(__file__)
with open(os.path.join(basedir, 'database.sql'), 'r') as f:
	schema = f.read()

# Create the directory if it doesn't exist
dirpath = sys.argv[1]
os.makedirs(dirpath, exist_ok=True)

# Check that the files don't exist - wouldn't want to overwrite anything important
paths = [os.path.join(dirpath, fname) for fname in 'config.py ca.pem service.cert service.key'.split()]
confpath, capath, certpath, keypath = paths
for path in paths:
	if os.path.exists(path):
		print(path, 'already exists!', file=sys.stderr)
		sys.exit(1)

# Make AivenCLI load the auth token for us
cli = AivenCLI()
cli.run(args=['user', 'info'])

project = cli.get_project()
cli = cli.client

# Create the needed services
print('Creating services...')
AivenCLI().run(args='service create webmonitor-pg -t pg --plan hobbyist'.split())
AivenCLI().run(args='service create webmonitor-kafka -t kafka --plan startup-2'.split())
print('Services created')

ca = cli.get_project_ca(project)
kafka = cli.get_service(project, 'webmonitor-kafka')
pg = cli.get_service(project, 'webmonitor-pg')

kafkaparams = kafka['service_uri_params']
pgparams = pg['service_uri_params']
pgparams['dsn'] = 'host=%s port=%s user=%s password=%s dbname=%s' % (
	pgparams['host'], pgparams['port'], pgparams['user'], pgparams['password'], pgparams['dbname']
)

config = """
import aiokafka.helpers
import aiohttp
import os

BASE = os.path.dirname(__file__)

PG_DSN = %r
KAFKA_OPTS = {
	'bootstrap_servers': '%s:%s',
	'security_protocol': 'SSL',
	'ssl_context': aiokafka.helpers.create_ssl_context(
		cafile=os.path.join(BASE, 'ca.pem'),
		certfile=os.path.join(BASE, 'service.cert'),
		keyfile=os.path.join(BASE, 'service.key'),
	)
}

CHECK_FREQUENCY = 1
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=10)
BATCH_SIZE = 10

URLS = [
	#('https://aiven.io/', 'Learn More'),
	#('https://console.aiven.io/', None),
]
""" % (pgparams['dsn'], kafkaparams['host'], kafkaparams['port'])

files = [
	(confpath, config),
	(capath, ca['certificate']),
	(certpath, kafka['connection_info']['kafka_access_cert']),
	(keypath, kafka['connection_info']['kafka_access_key']),
]
for path, data in files:
	with open(path, 'x') as f:
		f.write(data)

print('Configuration files written')
print('Waiting for postgresql to come up...')

AivenCLI().run(args='service wait webmonitor-pg'.split())
wait_for_dns(pgparams['host'])

conn = psycopg2.connect(pgparams['dsn'])
cur = conn.cursor()
cur.execute(schema)
conn.commit()

print('Database schema created')
print('Waiting for kafka to come up...')

AivenCLI().run(args='service wait webmonitor-kafka'.split())
wait_for_dns(kafkaparams['host'])

print('Creating kafka topic')
while True:
	try:
		cli.create_service_topic(project, 'webmonitor-kafka', 'webmonitor', 1, 3, 1, -1, 72, 'delete')
	except aiven.client.client.Error as e:
		print('Got', e, 'retrying in 10 seconds...')
		time.sleep(10)
	break

print('Kafka topic created')
print()

print('The services have now been fully set up, as far as the automated stuff goes')
print('Please edit', confpath, 'to add the urls you want to monitor')
print('After that, you can start the programs with:')
print('python -m webmonitor.producer', os.path.realpath(confpath))
print('python -m webmonitor.consumer', os.path.realpath(confpath))

