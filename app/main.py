from fastapi import FastAPI
from starlette import status

app = FastAPI()


@app.get("/healthy", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "Healthy"}
