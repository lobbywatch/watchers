import sys
from os.path import dirname, realpath
sys.path.append(dirname(realpath(__file__)))

import json
import regex as re
import logging
import time
from datetime import datetime
from typing import Any, TypedDict, Union, Dict

import requests
from slack_sdk import WebClient
from webchanges import reporters
from webchanges.filters import FilterBase
from webchanges.handler import JobState
from webchanges.jobs import JobBase

from namematch.namematcher import MatchFormat, NameMatcher, Name
from namematch.lobbywatch import PersonType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ConfigReportWaybackMachine = TypedDict(
    'ConfigReportWaybackMachine',
    {
        'enabled': bool,
        'sleep': int,
    },
)


class NameMatchFilter(FilterBase):
    __kind__ = 'name_match'
    parl_names = []
    with open('parliamentarians.ndjson', 'r', encoding='utf-8') as f:
        for line in f:
            parl_names.append(json.loads(line, object_hook=lambda d: Name(id=(PersonType.PARLIAMENTARIAN, d['id']), first=d['first'],
                                                                          middle=tuple(d['middle'].split(' ')) if d['middle'] else None, nick=d['nick'], last=d['last'],
                                                                          citizenships=None)))

    lobby_names = []
    with open('lobbyists.ndjson', 'r', encoding='utf-8') as f:
        for line in f:
            lobby_names.append(json.loads(line, object_hook=lambda d: Name(id=(PersonType.LOBBYIST, d['id']), first=d['first'],
                                                                           middle=tuple(d['middle'].split(' ')) if d['middle'] else None, nick=d['nick'], last=d['last'],
                                                                           citizenships=None)))

    parl_matcher = NameMatcher(parl_names, formats=[MatchFormat.NAME_ONLY])
    lobby_matcher = NameMatcher(lobby_names, formats=[MatchFormat.NAME_ONLY])

    def __init__(self, job: JobBase, state: JobState) -> None:
        super().__init__(job, state)

    def filter(self, data: Union[str, bytes], subfilter: Dict[str, Any], **kwargs) -> str:

        stdin = data.replace('\xc2\xa0', ' ').replace(' ', ' ')
        matches = NameMatchFilter.parl_matcher.match_content(stdin.encode(encoding='utf-8'), label=None, offset=0, format=MatchFormat.NAME_ONLY)
        matches += NameMatchFilter.lobby_matcher.match_content(stdin.encode(encoding='utf-8'), label=None, offset=0, format=MatchFormat.NAME_ONLY)
        matches.sort(key=lambda m: m.start)
        result = ''
        for m in matches:
            emoji = m.name.id[0].emoji if type(m.name.id) is tuple else ''
            result += re.sub('\\s+', ' ', f'{emoji}{str(m.message[m.start:m.end], "utf-8")}{emoji}') + '\n'
        return result


class CustomSlackReporter(reporters.TextReporter):
    """Custom Slack reporter that uploads diff as file to Slack"""

    __kind__ = 'custom_slack'

    def submit(self):
        text = '\n'.join(super().submit())
        if text:
            slack_token = self.config['token']
            client = WebClient(token=slack_token)
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            response = client.files_upload(
                channels=self.config['channel'],
                filetype="diff",
                content=text,
                initial_comment="Report " + timestamp,
                title=f"report-{datetime.now().strftime('%d.%m.%Y')}.txt"
            )


class WaybackMachineReporter(reporters.ReporterBase):
    """Adds a snapshot of all changed / new pages to archive.org"""

    __kind__ = 'wayback_machine'

    config: ConfigReportWaybackMachine

    def submit(self):
        sleep = self.config['sleep'] if self.config['sleep'] else 0
        for job_state in self.report.get_filtered_job_states(self.job_states):
            if job_state.exception:
                continue
            location = job_state.job.get_location()
            logger.info(f"Adding snapshot to archive.org for: {location}")
            try:
                req = requests.head(f"https://web.archive.org/save/{location}")
                if req.ok:
                    logger.info(f"Snapshot at: {req.headers['location']}")
                else:
                    logger.error(f"Failed to create snapshot for {location}: {req.headers}")
                if sleep > 0:
                    time.sleep(sleep)
            except requests.RequestException as e:
                logger.error(f"Submission failed for {location}: {e=}, {type(e)=}")
