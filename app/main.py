import os
import secrets
import string
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, HttpUrl
from sqlalchemy.orm import Session

from app.database import URL, get_db

load_dotenv()

app = FastAPI()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


class URLCreate(BaseModel):
    original_url: HttpUrl


class URLResponse(BaseModel):
    id: int
    short_code: str
    short_url: str
    original_url: HttpUrl
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@app.get("/")
def root():
    return {"message": "URL Shortener API is running"}


@app.post("/urls", response_model=URLResponse)
def create_url(
    url: URLCreate,
    db: Session = Depends(get_db),
):
    characters = string.ascii_letters + string.digits

    while True:
        short_code = "".join(
            secrets.choice(characters)
            for _ in range(6)
        )

        existing_url = (
            db.query(URL)
            .filter(URL.short_code == short_code)
            .first()
        )

        if not existing_url:
            break

    new_url = URL(
        short_code=short_code,
        original_url=str(url.original_url),
    )

    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    return {
        "id": new_url.id,
        "short_code": new_url.short_code,
        "short_url": f"{BASE_URL.rstrip('/')}/{new_url.short_code}",
        "original_url": new_url.original_url,
        "created_at": new_url.created_at,
    }


@app.get("/{short_code}")
def redirect_url(
    short_code: str,
    db: Session = Depends(get_db),
):
    url = (
        db.query(URL)
        .filter(URL.short_code == short_code)
        .first()
    )

    if not url:
        raise HTTPException(
            status_code=404,
            detail="URL not found",
        )

    return RedirectResponse(
        url.original_url,
        status_code=302,
    )
