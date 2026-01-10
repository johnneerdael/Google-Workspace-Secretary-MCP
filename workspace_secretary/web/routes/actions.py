from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from workspace_secretary.web import engine_client as engine

router = APIRouter(prefix="/api/email")


@router.post("/toggle-read/{folder}/{uid}")
async def toggle_read(folder: str, uid: int, mark_unread: bool = Query(False)):
    if mark_unread:
        result = await engine.mark_unread(uid, folder)
    else:
        result = await engine.mark_read(uid, folder)
    return JSONResponse(result)


@router.post("/move/{folder}/{uid}")
async def move_email(folder: str, uid: int, destination: str = Query(...)):
    result = await engine.move_email(uid, folder, destination)
    return JSONResponse(result)


@router.post("/delete/{folder}/{uid}")
async def delete_email(folder: str, uid: int):
    result = await engine.delete_email(uid, folder)
    return JSONResponse(result)


@router.post("/labels/{folder}/{uid}")
async def modify_labels(
    folder: str, uid: int, labels: str = Query(...), action: str = Query("add")
):
    label_list = [l.strip() for l in labels.split(",") if l.strip()]
    result = await engine.modify_labels(uid, folder, label_list, action)
    return JSONResponse(result)
