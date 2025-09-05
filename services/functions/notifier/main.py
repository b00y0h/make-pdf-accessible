from fastapi import FastAPI

app = FastAPI(
    title="PDF notifier Service",
    description="Microservice for PDF notifier functionality",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF notifier service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
