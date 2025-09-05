from fastapi import FastAPI

app = FastAPI(
    title="PDF tagger Service",
    description="Microservice for PDF tagger functionality",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF tagger service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
