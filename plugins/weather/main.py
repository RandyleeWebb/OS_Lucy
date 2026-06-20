from fastapi import FastAPI

app = FastAPI()

@app.get("/weather")
def weather(city: str):
    return {"temp_c": 23.5, "city": city}
