import logging
from datetime import datetime
import time

import requests
from slack_sdk import WebClient
from webchanges import reporters

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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

    def submit(self):
        for job_state in self.report.get_filtered_job_states(self.job_states):
            location = job_state.job.get_location()
            logger.info(f"Adding snapshot to archive.org for: {location}")
            try:
                req = requests.head(f"https://web.archive.org/save/{location}")
                if req.ok:
                    logger.info(f"Snapshot at: {req.headers['location']}")
                else:
                    logger.error(f"Failed to create snapshot for {location}: {req.headers}")
                time.sleep(4)
            except requests.RequestException as e:
                logger.error(f"Submission failed for {location}: {e=}, {type(e)=}")
