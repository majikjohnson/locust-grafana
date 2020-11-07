from influxdb import InfluxDBClient
import locust.env
from locust.exception import CatchResponseError
import gevent
import csv
import os
from datetime import datetime, timezone
import configparser
from typing import List
import numpy as np
import greenlet


class InfluxListener:

    def __init__(self, env: locust.env.Environment, config):
        self._finished = False
        self._line_tracker = 0
        self._config = configparser.ConfigParser()
        self._config.read(config)
        host = self._config["influxdb"]["host"]
        port = int(self._config["influxdb"]["port"])
        self._client = InfluxDBClient(host=host, port=port)
        self._client.switch_database("locust")
        self.env = env
        self._samples: List[dict] = []
        self._background = gevent.spawn(self._run)
        events = self.env.events
        events.request_success.add_listener(self.request_success)
        events.request_failure.add_listener(self.request_failure)
        events.quitting.add_listener(self.quitting)

    def _run(self):
        while True:
            samples_buffer = self._samples
            self._samples = []
            self._write_samples_to_db(samples_buffer)
            # self._write_results_to_db()
            if self._finished:
                break
            gevent.sleep(1)

    def _write_samples_to_db(self, samples):
        sample_dict = {}

        for sample in samples:
            if sample["request_type"] == "N/A":
                continue
            name = sample["name"]
            greenlet_id = str(sample["greenlet"])
            response_time = sample["response_time"]
            length = sample["response_length"]
            failure = sample["failure"]

            if greenlet_id not in sample_dict:
                response_times = []
                response_times.append(response_time)
                lengths = []
                lengths.append(length)
                sample_dict[greenlet_id] = {
                    name: {
                        "name": name,
                        "greenlet": greenlet_id,
                        "request_type": sample["request_type"],
                        "response_time_samples": response_times,
                        "length_samples": lengths,
                        "min_response_time": response_time,
                        "max_response_time": response_time,
                        "total_requests": 1,
                        "total_failures": failure
                    }
                }
            else:
                if name not in sample_dict[greenlet_id]:
                    response_times = []
                    response_times.append(response_time)
                    lengths = []
                    lengths.append(length)

                    sample_dict[greenlet_id][name] = {
                        "name": name,
                        "greenlet": greenlet_id,
                        "request_type": sample["request_type"],
                        "response_time_samples": response_times,
                        "length_samples": lengths,
                        "min_response_time": response_time,
                        "max_response_time": response_time,
                        "total_requests": 1,
                        "total_failures": failure
                    }
                else:
                    sample_dict[greenlet_id][name]["response_time_samples"].append(
                        response_time)
                    sample_dict[greenlet_id][name]["length_samples"].append(length)
                    sample_dict[greenlet_id][name]["total_requests"] += 1
                    sample_dict[greenlet_id][name]["total_failures"] += failure
                    if response_time > sample_dict[greenlet_id][name]["max_response_time"]:
                        sample_dict[greenlet_id][name]["max_response_time"] = response_time
                    if response_time < sample_dict[greenlet_id][name]["min_response_time"]:
                        sample_dict[greenlet_id][name]["min_response_time"] = response_time

        json_body = []
        for greenlet_id in sample_dict:
            for name in sample_dict[greenlet_id]:
                sample_dict[greenlet_id][name]["average_response_time"] = np.mean(
                    sample_dict[greenlet_id][name]["response_time_samples"])
                sample_dict[greenlet_id][name]["median_response_time"] = np.percentile(
                    sample_dict[greenlet_id][name]["response_time_samples"], 50)
                sample_dict[greenlet_id][name]["90_percentile"] = np.percentile(
                    sample_dict[greenlet_id][name]["response_time_samples"], 90)
                sample_dict[greenlet_id][name]["95_percentile"] = np.percentile(
                    sample_dict[greenlet_id][name]["response_time_samples"], 95)
                sample_dict[greenlet_id][name]["avg_content_length"] = round(
                    np.mean(sample_dict[greenlet_id][name]["length_samples"]))
                sample_dict[greenlet_id][name]["min_response_time"] = np.amin(
                    sample_dict[greenlet_id][name]["response_time_samples"])
                sample_dict[greenlet_id][name]["max_response_time"] = np.amax(
                    sample_dict[greenlet_id][name]["response_time_samples"])

                json_body.append({
                    "measurement": "requests_v2",
                    "tags": {
                        "request_type": sample_dict[greenlet_id][name]["request_type"],
                        "name": sample_dict[greenlet_id][name]["name"],
                        "worker_id": os.getenv("WORKER_ID", "default"),
                        "greenlet": greenlet_id
                    },
                    "fields": {
                        "avg_response_time":
                            sample_dict[greenlet_id][name]["average_response_time"],
                        "median_response_time":
                            sample_dict[greenlet_id][name]["median_response_time"],
                        "90_percentile": sample_dict[greenlet_id][name]["90_percentile"],
                        "95_percentile": sample_dict[greenlet_id][name]["95_percentile"],
                        "min_response_time":
                            sample_dict[greenlet_id][name]["min_response_time"],
                        "max_response_time":
                            sample_dict[greenlet_id][name]["max_response_time"],
                        "avg_content_length":
                            sample_dict[greenlet_id][name]["avg_content_length"],
                        "requests_per_second": sample_dict[greenlet_id][name]["total_requests"],
                        "failures_per_second": sample_dict[greenlet_id][name]["total_failures"],

                    },
                    "time": sample["time"]
                })
        self._client.write_points(json_body)

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

    def request_success(self, request_type, name, response_time,
                        response_length, **_kwargs):
        self._log_request(request_type, name, response_time,
                          response_length, 0, None)

    def request_failure(self, request_type, name, response_time,
                        response_length, exception, **_kwargs):
        self._log_request(request_type, name, response_time,
                          response_length, 1, exception)

    def _log_request(self, request_type, name, response_time,
                     response_length, failure, exception):

        current_greenlet = greenlet.getcurrent()  # pylint: disable=I1101
        if hasattr(current_greenlet, "minimal_ident"):
            greenlet_id = current_greenlet.minimal_ident
        else:
            greenlet_id = -1  # if no greenlet has been spawned (typically when debugging)
        
        sample = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "greenlet": greenlet_id,
            "request_type": request_type,
            "name": name,
            "failure": failure,
            "response_time": response_time,
        }

        if response_length >= 0:
            sample["response_length"] = response_length
        else:
            sample["response_length"] = None

        if exception:
            if isinstance(exception, CatchResponseError):
                sample["exception"] = str(exception)
            else:
                try:
                    sample["exception"] = repr(exception)
                except AttributeError:
                    sample["exception"] = f"{exception.__class__}"
        else:
            sample["exception"] = None

        self._samples.append(sample)

    def quitting(self, **_kwargs):
        self._finished = True
        self._background.join(timeout=10)
