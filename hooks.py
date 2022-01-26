from datetime import datetime

from slack_sdk import WebClient
from urlwatch import reporters


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
