import sys
from os.path import dirname, realpath

sys.path.append(dirname(realpath(__file__)))

import io
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Iterable, TypedDict

import regex as re
import requests
from minio import Minio
from webchanges import reporters
from webchanges.filters import FilterBase

from namematch.lobbywatch import PersonType
from namematch.namematcher import MatchFormat, Name, NameMatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ConfigReportWaybackMachine = TypedDict(
    "ConfigReportWaybackMachine",
    {
        "enabled": bool,
        "sleep": int,
    },
)


class NameMatchFilter(FilterBase):
    """Custom filter to match persons from lobbywatch's database"""

    __kind__ = "name_match"
    parl_names = []
    with open("parliamentarians.ndjson", "r", encoding="utf-8") as f:
        for line in f:
            parl_names.append(
                json.loads(
                    line,
                    object_hook=lambda d: Name(
                        id=(PersonType.PARLIAMENTARIAN, d["id"]),
                        first=d["first"],
                        middle=tuple(d["middle"].split(" ")) if d["middle"] else None,
                        nick=d["nick"],
                        last=d["last"],
                        citizenships=None,
                    ),
                )
            )

    lobby_names = []
    with open("lobbyists.ndjson", "r", encoding="utf-8") as f:
        for line in f:
            lobby_names.append(
                json.loads(
                    line,
                    object_hook=lambda d: Name(
                        id=(PersonType.LOBBYIST, d["id"]),
                        first=d["first"],
                        middle=tuple(d["middle"].split(" ")) if d["middle"] else None,
                        nick=d["nick"],
                        last=d["last"],
                        citizenships=None,
                    ),
                )
            )

    parl_matcher = NameMatcher(parl_names, formats=[MatchFormat.NAME_ONLY])
    lobby_matcher = NameMatcher(lobby_names, formats=[MatchFormat.NAME_ONLY])

    @staticmethod
    def filter(
        data: str | bytes, mime_type: str, subfilter: dict[str, Any]
    ) -> tuple[str | bytes, str]:
        stdin = data.replace("\xc2\xa0", " ").replace(" ", " ")
        matches = NameMatchFilter.parl_matcher.match_content(
            stdin.encode(encoding="utf-8"),
            label=None,
            offset=0,
            format=MatchFormat.NAME_ONLY,
        )
        matches += NameMatchFilter.lobby_matcher.match_content(
            stdin.encode(encoding="utf-8"),
            label=None,
            offset=0,
            format=MatchFormat.NAME_ONLY,
        )
        matches.sort(key=lambda m: m.start)
        result = ""
        for m in matches:
            emoji = m.name.id[0].emoji if type(m.name.id) is tuple else ""
            result += (
                re.sub(
                    "\\s+",
                    " ",
                    f"{emoji}{str(m.message[m.start : m.end], 'utf-8')}{emoji}",
                )
                + "\n"
            )
        return result, mime_type


class WaybackMachineReporter(reporters.ReporterBase):
    """Adds a snapshot of all changed / new pages to archive.org"""

    __kind__ = "wayback_machine"

    config: ConfigReportWaybackMachine

    def submit(self, **kwargs: Any) -> Iterable[str]:
        sleep = self.config["sleep"] if self.config["sleep"] else 0
        for job_state in self.report.get_filtered_job_states(self.job_states):
            if job_state.exception:
                continue
            location = job_state.job.get_location()
            logger.info("Adding snapshot to archive.org for: %s", location)
            try:
                req = requests.head(
                    f"https://web.archive.org/save/{location}", timeout=30
                )
                if req.ok:
                    logger.info("Snapshot at: %s", req.headers["location"])
                else:
                    logger.error(
                        "Failed to create snapshot for %s: %s", location, req.headers
                    )
                if sleep > 0:
                    time.sleep(sleep)
            except requests.RequestException as e:
                logger.error("Submission failed for %s: %s", location, e)


class ObjectStorageUploader(reporters.HtmlReporter):
    """Custom reporter that uploads the HTML report to an S3-compatible object storage
    and (optionally) posts the URL into a Mattermost channel.

    .. code-block:: yaml

       report:
         object_storage_uploader:
           enabled: true
    """

    __kind__ = "object_storage_uploader"

    def submit(self, **kwargs: Any) -> Iterable[str]:
        endpoint = os.environ["OBJECT_STORAGE_UPLOADER_ENDPOINT"]
        bucket_name = os.environ["OBJECT_STORAGE_UPLOADER_BUCKET_NAME"]
        access_key = os.environ["OBJECT_STORAGE_UPLOADER_ACCESS_KEY"]
        secret_key = os.environ["OBJECT_STORAGE_UPLOADER_SECRET_KEY"]
        region = "us-east-1"
        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            secure=True,
        )
        logger.info("uploading report to %s", endpoint)

        object_name = f"reports/{datetime.now().isoformat()}-report.html"
        s = "\n".join(super().submit())
        data = io.BytesIO(s.encode("utf-8"))

        result = client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=data,
            length=len(s),
            content_type="text/html",
        )

        logger.info('object "%s" uploaded', object_name)

        webhook = os.environ.get("OBJECT_STORAGE_UPLOADER_NOTIFY_WEBHOOK")

        if webhook:
            link = f"https://{endpoint}/{bucket_name}/{result.object_name}"
            res = requests.post(webhook, data={"text": link}, timeout=10)
            if res.ok:
                logger.info("notified webhook about upload")
            else:
                logger.error(
                    "failed to notify webhook: %s (status %s)",
                    res.text,
                    res.status_code,
                )
