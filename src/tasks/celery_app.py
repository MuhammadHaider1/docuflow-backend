from celery import Celery

app = Celery(
    "docuflow_celery",
    broker="redis://localhost:6380/0",
    backend="redis://localhost:6380/1",
    include=["src.tasks.document_tasks"],
)

app.autodiscover_tasks(["src.tasks"])

if __name__ == "__main__":
    app.start()

import src.tasks.document_tasks  # noqa: E402, F401
