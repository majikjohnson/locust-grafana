from locust import HttpUser, task, between, events, LoadTestShape
from common.influx_listener import InfluxListener
import locust.stats
import math


class StepLoadShape(LoadTestShape):
    """
    A step load shape
    Keyword arguments:
        step_time -- Time between steps
        step_load -- User increase amount at each step
        spawn_rate -- Users to stop/start per second at every step
        time_limit -- Time limit in seconds
    """

    step_time = 30
    step_load = 10
    spawn_rate = 10
    time_limit = 600

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        current_step = math.floor(run_time / self.step_time) + 1
        return (current_step * self.step_load, self.spawn_rate)


class MyUser(HttpUser):
    wait_time = between(1, 5)
    host = "https://testingninja.co.uk/"
    locust.stats.CSV_STATS_FLUSH_INTERVAL_SEC = 5

    @task()
    def load_homepage(self):
        self.client.get("/", name="homepage")

    @task()
    def load_blog_entry(self):
        self.client.get(
            "/2019/11/11/"
            "deploy-a-react-app-using-github-travis-ci-and-heroku/",
            name="blog post"
        )


@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    InfluxListener(env=environment)
