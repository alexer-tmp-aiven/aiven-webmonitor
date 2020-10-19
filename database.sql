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

CREATE FUNCTION insert_event (ts TIMESTAMP, url TEXT, ok BOOLEAN, http_status INTEGER, response_time DOUBLE PRECISION, content_ok BOOLEAN, error TEXT) RETURNS VOID AS $$
DECLARE
	event_id INT;
BEGIN
	-- As per https://www.postgresql.org/message-id/200909261156.12172.aklaver@comcast.net
	INSERT INTO events (timestamp, url, ok) VALUES (ts, url, ok) RETURNING id INTO event_id;

	IF ok THEN
		INSERT INTO results (event_id, http_status, response_time, content_ok) VALUES (event_id, http_status, response_time, content_ok);
	ELSE
		INSERT INTO errors (event_id, error) VALUES (event_id, error);
	END IF;
END;
$$ LANGUAGE plpgsql;

