from fastapi import FastAPI

app = FastAPI(
    title="PDF exporter Service",
    description="Microservice for PDF exporter functionality",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF exporter service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
