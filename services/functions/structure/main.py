from fastapi import FastAPI

app = FastAPI(
    title="PDF structure Service",
    description="Microservice for PDF structure functionality",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF structure service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
