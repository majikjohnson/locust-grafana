from influxdb import InfluxDBClient
import locust.env
import gevent
import csv
from datetime import datetime, timezone


class InfluxListener:

    def __init__(self, env: locust.env.Environment):
        self._finished = False
        self._line_tracker = 0
        self._client = InfluxDBClient(host='localhost', port=8086)
        self._client.switch_database('locust')
        self.env = env
        self._background = gevent.spawn(self._run)
        events = self.env.events
        events.quitting.add_listener(self.quitting)

    def _run(self):
        while True:
            self._write_results_to_db()
            if self._finished:
                break
            gevent.sleep(5)

    def _write_results_to_db(self):
        json_body = []
        with open("example_stats_history.csv", newline='') as f:
            stats = csv.reader(f)
            lines_in_file = 0
            for index, line in enumerate(stats):
                if index > self._line_tracker:
                    if line[6] == "N/A":
                        lines_in_file = index
                        continue
                    json_body.append({
                        "measurement": line[3],
                        "tags": {
                            "user_count": line[1],
                        },
                        "fields": {
                            "rps": float(line[4]),
                            "fps": float(line[5]),
                            "median": int(line[6]),
                            "66_percentile": int(line[7]),
                            "75_percentile": int(line[8]),
                            "80_percentile": int(line[9]),
                            "90_percentile": int(line[10]),
                            "95_percentile": int(line[11]),
                            "98_percentile": int(line[12]),
                            "99_percentile": int(line[13]),
                            "99_9_percentile": int(line[14]),
                            "90_99_percentile": int(line[15]),
                            "100_percentile": int(line[16]),
                        },
                        "time": datetime.fromtimestamp(
                            int(line[0]),
                            timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                    })
                lines_in_file = index
            self._line_tracker = lines_in_file
            self._client.write_points(json_body)

    def quitting(self, **_kwargs):
        self._finished = True
        self._background.join(timeout=10)
