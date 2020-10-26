from locust import HttpUser, task, between, events
from common.influx_listener import InfluxListener


class MyUser(HttpUser):
    wait_time = between(1, 5)
    host = "https://testingninja.co.uk/"

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
