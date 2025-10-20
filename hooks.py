import sys
from os.path import dirname, realpath
sys.path.append(dirname(realpath(__file__)))

import json
import logging
import time
from typing import Any, Iterable, TypedDict

import regex as re
import requests
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
