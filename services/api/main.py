from fastapi import FastAPI

app = FastAPI(
    title="PDF Accessibility API",
    description="Main API gateway for PDF accessibility services",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "PDF Accessibility API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
