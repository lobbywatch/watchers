#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import subprocess
from datetime import date
from urllib.parse import urlparse

from unicodedata import normalize
from dotenv import dotenv_values
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Install the Slack app and get xoxb- token in advance
config = dotenv_values(".env")
app = App(token=config["SLACK_BOT_TOKEN"])
logging.basicConfig(level=logging.DEBUG)

@app.command("/add-website")
def add_website(ack, body, respond, command, logger):
    ack()
    logger.info(body)
    if command.get("text"):
        respond(add_website(command["text"]))


def add_website(text):
    url = None
    if text.startswith("<") and text.endswith(">"):
        url = urlparse(text[1:-1])
    if not url or not url.scheme.startswith("http") or not url.netloc:
        return f"Invalid URL: {text}"

    process = subprocess.run(['./add-url.sh', url.geturl()], stdout=subprocess.PIPE, universal_newlines=True)
    result = process.stdout
    if process.returncode == 0:
        if not result.startswith("URL already added:"):
            subprocess.run(['bash', '-c', f'git add urls.yaml'])
            subprocess.run(['bash', '-c', f'git commit -m "adding {url.geturl()}"'])
            subprocess.run(['bash', '-c', f'git push'])
    return result


@app.event("app_mention")
def handle_mention(body, say, logger):
    logger.debug(body)
    if body.get('text') and body.text.find('add-website') > 0:
        text = normalize("NFKD", body.text)
        url = text[text.find('add-website') + len('add-website'):]
        if url.find(' ') > 0:
            url = url[:url.find(' ')]
        say(add_website(url), thread_ts=body["event"]["event_ts"])
    else:
        say('Sorry, I only respond to messages containing the text "add-website <url>"', thread_ts=body["event"]["event_ts"], ephemeral_user=True)


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
