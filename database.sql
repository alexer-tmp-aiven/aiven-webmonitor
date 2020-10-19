CREATE TABLE events (
	id SERIAL PRIMARY KEY,
	timestamp TIMESTAMP NOT NULL,
	url TEXT NOT NULL,
	ok BOOLEAN NOT NULL
);

CREATE TABLE results (
	event_id INTEGER NOT NULL REFERENCES events (id),
	http_status CHAR(3) NOT NULL,
	response_time DOUBLE PRECISION NOT NULL,
	content_ok BOOLEAN
);

CREATE TABLE errors (
	event_id INTEGER NOT NULL REFERENCES events (id),
	error TEXT NOT NULL
);

