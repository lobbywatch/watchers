import json
import logging
import os
from typing import Dict, List, Annotated

import requests
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel, HttpUrl

import nameloader
from namematcher import MatchFormat, NameMatch, NameMatcher

app = FastAPI()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


WEBHOOK_URL = os.environ["OBJECT_STORAGE_UPLOADER_NOTIFY_WEBHOOK"]
ACCESS_TOKEN = os.environ["WW_ACCESS_TOKEN"]


class ChangeNotification(BaseModel):
    model_config = {"extra_args": False}
    watch_url: HttpUrl
    diff: bytes
    diff_url: HttpUrl


@app.post("/change")
async def receive_change(
    change_notification: ChangeNotification,
    background_tasks: BackgroundTasks,
    x_access_token: Annotated[str | None, Header()] = None,
):
    if x_access_token != ACCESS_TOKEN:
        raise HTTPException(status_code=401)

    background_tasks.add_task(check_for_matches, change_notification)
    return {"ok": True}


def check_for_matches(change_notification: ChangeNotification):
    names = nameloader.get_names()
    matcher = NameMatcher(names, [MatchFormat.NAME_ONLY])
    matches = matcher.match_text(change_notification.diff, MatchFormat.NAME_ONLY)
    if matches:
        notify_chat(change_notification, matches)
    else:
        logger.info("no matches, not notifying", change_notification)


def notify_chat(
    change_notification: ChangeNotification, matches: List[NameMatch]
) -> None:
    data = build_chat_message(change_notification, matches)
    res = requests.post(
        WEBHOOK_URL,
        data=json.dumps(data),
        headers={"content-type": "application/json"},
        timeout=10,
    )
    if res.ok:
        logger.info("notified webhook about upload")
    else:
        logger.error(
            "failed to notify webhook: %s (status %s)",
            res.text,
            res.status_code,
        )


def build_chat_message(
    change_notification: ChangeNotification, matches: List[NameMatch]
) -> Dict:
    diff_url = HttpUrl.build(
        scheme=change_notification.diff_url.scheme,
        host=change_notification.diff_url.host,
        path=change_notification.diff_url.path[
            1:
        ],  # skip lead slash, otherwise there will be two of them
        query="type=diffLines&removed=on&added=on&replaced=on#text",
    ).encoded_string()
    watch_url = change_notification.watch_url.encoded_string()
    names = (
        "".join(
            [
                f"{m.name.id[0].emoji} {m.name.first} {m.name.last} {m.name.id[0].emoji}"
                for m in matches
            ]
        )
        if matches
        else "keine"
    )
    return {
        "attachments": [
            {
                "title": f"Änderung bei {watch_url}",
                "fields": [
                    {"title": "Gefundene Personen", "value": names, "short": False},
                    {
                        "title": "Details zur Änderung",
                        "value": diff_url,
                        "short": False,
                    },
                ],
            }
        ]
    }
