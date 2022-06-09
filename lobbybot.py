#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import subprocess
from datetime import date
from urllib.parse import urlparse

from dotenv import dotenv_values
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.respond.respond import Respond
from unicodedata import normalize

# Install the Slack app and get xoxb- token in advance
config = dotenv_values(".env")
app = App(token=config["SLACK_BOT_TOKEN"])
logging.basicConfig(level=logging.DEBUG)


@app.command("/add-website")
def add_website(ack, body, respond, command, logger):
    ack()
    logger.info(body)
    if "text" in command:
        respond(add_website(command["text"], logger))


def add_website(text, logger):
    url = None
    if text.startswith("<") and text.endswith(">"):
        url = urlparse(text[1:-1])
    if not url or not url.scheme.startswith("http") or not url.netloc:
        return f"Invalid URL: {text}"

    logger.debug(f'adding website: {url.geturl()}')
    process = subprocess.run(['bash', '-c', f'./add-url.sh {url.geturl()}'], stdout=subprocess.PIPE, universal_newlines=True)
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
    if body['event']['text'].find('add-website') > 0:
        text = normalize("NFKD", body['event']['text'])
        url = text[text.find('add-website') + len('add-website'):].strip()
        if url.find(' ') > 0:
            url = url[:url.find(' ')]
        say(add_website(url, logger), thread_ts=body["event"]["event_ts"])
    else:
        say('Sorry, I only respond to messages containing the text "add-website <url>"', thread_ts=body["event"]["event_ts"],
            ephemeral_user=True)


initial_messages = {}


@app.action(re.compile("tweet_edit_(de|fr)"))
def tweet_edit(ack, body, respond, logger):
    ack()
    logger.debug(body)
    initial_messages[body["response_url"]] = body['message']

    if "trigger_id" not in body:
        pass

    lang = 'de' if body['actions'][0]['action_id'] == 'tweet_edit_de' else 'fr'
    app.client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            # View identifier
            "callback_id": "tweet_edit_view_" + lang,
            "private_metadata": body["response_url"],
            "title": {"type": "plain_text", "text": "Lobbybot"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Hier kann der *{'deutsche' if lang == 'de' else 'französische'}* Tweet bearbeitet werden"
                    }
                },
                {
                    "type": "input",
                    "block_id": "tweet_input_block",
                    "label": {"type": "plain_text", "text": "Tweet Text"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "tweet_text",
                        "initial_value": body['message']['blocks'][0]['fields'][2 if lang == 'de' else 3]['text'],
                        "multiline": True,
                        "focus_on_load": True
                    }
                }
            ]
        }
    )


@app.view(re.compile("tweet_edit_view_(de|fr)"))
def handle_submission(ack, body, client, view, logger):
    # Assume there's an input block with `input_c` as the block_id and `dreamy_input`
    tweet_text = view["state"]["values"]["tweet_input_block"]["tweet_text"]['value']
    user = body["user"]["id"]
    # Validate the inputs
    errors = {}
    if tweet_text is not None and len(tweet_text) > 280:
        errors["tweet_input_block"] = f"Der Tweet darf nicht länger als 280 Zeichen sein: {len(tweet_text)}"
    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return
    # Acknowledge the view_submission request and close the modal
    ack()
    # Do whatever you want with the input data - here we're saving it to a DB
    # then sending the user a verification of their submission

    # Message to send user
    msg = ""
    try:
        # Save to DB
        msg = f"Your submission of {tweet_text} was successful"
    except Exception as e:
        # Handle error
        msg = "There was an error with your submission"

    # logger.debug(body)

    lang = 'de' if body['view']['callback_id'] == 'tweet_edit_view_de' else 'fr'
    message = initial_messages[body['view']['private_metadata']]
    message['blocks'][0]['fields'][2 if lang == 'de' else 3]['text'] = tweet_text
    respond = Respond(response_url=body['view']['private_metadata'])
    respond(replace_original=True, blocks=message['blocks'])
    del initial_messages[body['view']['private_metadata']]


@app.action("tweet_post")
def tweet_post(ack, body, respond, logger):
    ack()
    body['message']['blocks'].pop()
    respond(replace_original=True, blocks=body['message']['blocks'])


@app.action("tweet_cancel")
def tweet_cancel(ack, body, respond, logger):
    ack()
    body['message']['blocks'].pop()
    del body['message']['blocks'][0]['fields']
    respond(replace_original=True, blocks=body['message']['blocks'])


@app.event("message")
def handle_message_events(ack, body, logger, say):
    ack()
    # logger.debug(body)
    if body['event']['channel_type'] == 'im' and "text" in body['event'] and body['event']['text'] == 'test':
        text_blocks = [
            {
                "type": "section",
                "text": {
                    "text": "Tweets für <https://cms.lobbywatch.ch/bearbeitung/interessenbindung.php?operation=view&pk0=13592|Gapany, Johanna - Netzwerk Future>",
                    "type": "mrkdwn"
                },
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Deutsch*"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Französisch*"
                    },
                    {
                        "type": "plain_text",
                        "text": "#LobbyNews Andri Silberschmidt (FDP/ZH) hat eine neue Interessenbindung: Vorstand bei Verein FDP-Kampagnen. Haben Sie das schon deklariert, @andrisilber? https://lobbywatch.ch/de/daten/parlamentarier/353/Andri%20Silberschmidt"
                    },
                    {
                        "type": "plain_text",
                        "text": "#LobbyNews Bonjour Andri Silberschmidt (FDP/ZH). Haben Sie das schon deklariert, @andrisilber? https://lobbywatch.ch/de/daten/parlamentarier/353/Andri%20Silberschmidt"
                    }
                ]
            },
            {
                "type": "actions",
                "block_id": "actionblock789",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Posten"
                        },
                        "style": "primary",
                        "value": "click_me_456",
                        "action_id": "tweet_post"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Bearbeiten DE"
                        },
                        "value": "click_me_456",
                        "action_id": "tweet_edit_de"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Bearbeiten FR"
                        },
                        "value": "click_me_456",
                        "action_id": "tweet_edit_fr"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Verwerfen"
                        },
                        "style": "danger",
                        "value": "click_me_456",
                        "action_id": "tweet_cancel"
                    },
                ]
            },
        ]
        say(text='dummy', blocks=text_blocks)


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
