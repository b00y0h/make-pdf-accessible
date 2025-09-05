from fastapi import FastAPI

app = FastAPI(
    title="PDF validator Service",
    description="Microservice for PDF validator functionality",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF validator service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
