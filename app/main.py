from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .routes import upload, login, result, upload_B_plan
from .models import models
from .database.database import engine
import uvicorn



app = FastAPI(debug=True)



# Adjust payload limit using middleware
@app.middleware("http")
async def limit_payload_size(request, call_next):
    if request.headers.get('content-length') and int(request.headers.get('content-length')) > 50 * 1024 * 1024:  # 50MB
        return JSONResponse(status_code=413, content={"message": "Payload too large"})
    return await call_next(request)


models.Base.metadata.create_all(bind = engine)

app.include_router(upload.router)
# app.include_router(login.router)
app.include_router(result.router)
app.include_router(upload_B_plan.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Fire Protection Review System API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)