from celery import Celery

app = Celery("pdf_worker")
app.config_from_object("celeryconfig")


@app.task
def process_pdf(file_path: str):
    """Process PDF file for accessibility"""
    return {"status": "processed", "file": file_path}
