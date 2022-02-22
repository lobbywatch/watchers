#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import subprocess
from datetime import date

from dotenv import dotenv_values
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Install the Slack app and get xoxb- token in advance
config = dotenv_values(".env")
app = App(token=config["SLACK_BOT_TOKEN"])
logging.basicConfig(level=logging.DEBUG)

@app.command("/hr")
def handle_some_command(ack, body, respond, command, logger):
    print(body)
    ack()
    logger.info(body)
    process = subprocess.run(['./add-url.sh', command["text"]], stdout=subprocess.PIPE, universal_newlines=True)
    logger.info(process.stdout)
    respond(f'hi {command["text"]}')


@app.event("app_mention")
def handle_mention(body, say, logger):
    user = body["event"]["user"]
    # single logger call
    # global logger is passed to listener
    logger.debug(body)
    say(f"{user} mentioned your app", thread_ts=body["event"]["event_ts"])


@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


@app.action(re.compile("[0-9]+"))
def handle_some_action(ack, body, respond, logger):
    handle_match_checkbox_selection(ack, body, respond, logger)


@app.action(re.compile("match_at_offset-[0-9]+"))
def handle_match_checkbox_selection(ack, body, respond, logger):
    ack()
    logger.info(body)
    for b in body["message"]["blocks"]:
        l = list(body["state"]["values"][b["block_id"]][b["accessory"]["action_id"]]["selected_options"])
        if l:
            b["accessory"]["initial_options"] = l
        else:
            b["accessory"].pop("initial_options", None)
    respond(replace_original=True, blocks=body["message"]["blocks"])

@app.action("datepicker123")
def handle_some_action(ack, body, logger):
    ack()
    logger.info(body)


@app.action("button123")
def handle_some_action(ack, body, respond, say, logger):
    ack()
    logger.info(body)
    print(body['view']['state']['values']['hr-input']['datepicker123']['selected_date'])
    respond(text='apa')


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    print(event)
    try:
        # views.publish is the method that your app uses to push a view to the Home tab
        client.views_publish(
            # the user that opened your app's app home
            user_id=event["user"],
            # the view object that appears in the app home
            view={
                "type": "home",
                "callback_id": "home_view",

                # body of the view
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Welcome to your _App's Home_* :tada:"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "This button won't do much for now but you can set up a listener for it using the `actions()` method and passing its unique `action_id`. See an example in the `examples` folder within your Bolt app."
                        }
                    },
                    {
                        "type": "actions",
                        "block_id": "hr-input",
                        "elements": [
                            {
                                "type": "datepicker",
                                "action_id": "datepicker123",
                                "initial_date": date.today().isoformat(),
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "Select a date"
                                }
                            },
                            {
                                "type": "button",
                                "action_id": "button123",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Click me!"
                                }
                            }
                        ]
                    }
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


if __name__ == "__main__":
    SocketModeHandler(app, config["SLACK_APP_TOKEN"]).start()
