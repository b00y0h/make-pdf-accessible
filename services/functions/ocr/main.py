from fastapi import FastAPI

app = FastAPI(
    title="PDF ocr Service",
    description="Microservice for PDF ocr functionality",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF ocr service is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
