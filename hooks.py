from datetime import datetime
import re
import requests
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from urlwatch import reporters


class CustomSlackReporter(reporters.TextReporter):
    """Custom Slack reporter that uploads diff as file to Slack"""

    __kind__ = 'custom_slack'

    def submit(self):
        slack_token = self.config['token']
        client = WebClient(token=slack_token)
        text = '\n'.join(super().submit())
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        response = client.files_upload(
            channels=self.config['channel'],
            filetype="diff",
            content=text,
            initial_comment="Report " + timestamp,
            title="report.txt"
        )
