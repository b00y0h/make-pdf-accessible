from fastapi import FastAPI

app = FastAPI(
    title="PDF router Service",
    description="Microservice for PDF router functionality",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF router service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
