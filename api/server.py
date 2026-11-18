
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import date
from typing import Optional
import time

from config import UNKNOWN_EVIDENCE_DIR

from database.db import (
    initialize_database,
    create_event,
    get_events,
    get_event_count,
    get_event_counts_by_type,
    search_events,
    get_event_by_id
)

from engine.security_engine import security_engine


app = FastAPI(
    title="SentinelGuard API",
    description="Offline AI security monitoring system",
    version="3.0.0"
)


class EventRequest(BaseModel):
    event_type: str
    track_id: Optional[int] = None
    person_name: Optional[str] = None
    similarity: Optional[float] = None
    evidence_path: Optional[str] = None
    description: Optional[str] = None


@app.on_event("startup")
def startup():
    initialize_database()
    security_engine.start()


@app.on_event("shutdown")
def shutdown():
    security_engine.stop()


@app.get("/")
def home():
    return {
        "system": "SentinelGuard",
        "status": "online",
        "mode": "offline"
    }


@app.get("/health")
def health():
    return {
        "api": "healthy",
        "camera": security_engine.get_status()
    }


@app.get("/camera/status")
def camera_status():
    return security_engine.get_status()


def video_generator():
    while True:
        frame = security_engine.get_frame()

        if frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame
                + b"\r\n"
            )

        time.sleep(0.04)


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        video_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/events")
def add_event(event: EventRequest):
    allowed_types = {
        "UNKNOWN_DETECTED",
        "UNKNOWN_ALERT",
        "AUTHORIZED_DETECTED",
        "SYSTEM"
    }

    if event.event_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported event type."
        )

    if (
        event.similarity is not None
        and not -1.0 <= event.similarity <= 1.0
    ):
        raise HTTPException(
            status_code=400,
            detail="Similarity must be between -1 and 1."
        )

    event_id = create_event(
        event_type=event.event_type,
        track_id=event.track_id,
        person_name=event.person_name,
        similarity=event.similarity,
        evidence_path=event.evidence_path,
        description=event.description
    )

    return {
        "success": True,
        "event_id": event_id
    }


@app.get("/events")
def list_events(
    event_type: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    allowed_types = {
        "UNKNOWN_DETECTED",
        "UNKNOWN_ALERT",
        "AUTHORIZED_DETECTED",
        "SYSTEM"
    }

    if event_type and event_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported event type."
        )

    for field_name, field_value in [
        ("date_from", date_from),
        ("date_to", date_to)
    ]:
        if field_value:
            try:
                date.fromisoformat(field_value)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"{field_name} must use YYYY-MM-DD format."
                )

    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from cannot be later than date_to."
        )

    if search and len(search) > 100:
        raise HTTPException(
            status_code=400,
            detail="Search text cannot exceed 100 characters."
        )

    return search_events(
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size
    )


@app.get("/events/{event_id}")
def event_details(event_id: int):
    if event_id < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid event ID."
        )

    event = get_event_by_id(event_id)

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found."
        )

    return event


@app.get("/stats")
def statistics():
    return {
        "total_events": get_event_count(),
        "event_counts": get_event_counts_by_type(),
        "database": "SQLite",
        "mode": "offline"
    }


@app.get("/evidence")
def list_evidence():
    events = get_events(500)
    evidence_items = []
    evidence_dir = UNKNOWN_EVIDENCE_DIR.resolve()

    for event in events:
        if event["event_type"] != "UNKNOWN_DETECTED":
            continue

        if not event["evidence_path"]:
            continue

        image_path = Path(event["evidence_path"]).resolve()

        if image_path.parent != evidence_dir:
            continue

        if image_path.suffix.lower() != ".jpg":
            continue

        if not image_path.is_file():
            continue

        evidence_items.append({
            "id": event["id"],
            "track_id": event["track_id"],
            "person_name": event["person_name"],
            "similarity": event["similarity"],
            "timestamp": event["timestamp"],
            "description": event["description"],
            "image_url": f"/evidence/{image_path.name}"
        })

    return {
        "total": len(evidence_items),
        "evidence": evidence_items
    }


@app.get("/evidence/{filename}")
def get_evidence_image(filename: str):
    if (
        Path(filename).name != filename
        or not filename.lower().endswith(".jpg")
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid evidence filename."
        )

    evidence_dir = UNKNOWN_EVIDENCE_DIR.resolve()
    image_path = (evidence_dir / filename).resolve()

    if image_path.parent != evidence_dir or not image_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Evidence image not found."
        )

    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg"
    )
