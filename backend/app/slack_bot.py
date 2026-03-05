"""Slack bot for BeccaBot. Run: python -m app.slack_bot

Requires SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env.
Uses Socket Mode (no public URL needed).
"""

import json
import re
import logging
import os

from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
CHAT_API_URL = os.getenv("BECCABOT_CHAT_API_URL", "http://127.0.0.1:8000/api/chat")


def run_slack_bot():
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logging.error(
            "SLACK_BOT_TOKEN and SLACK_APP_TOKEN required. Add to .env and run: python -m app.slack_bot"
        )
        return

    import urllib.request

    def call_chat(message: str, history: list[dict] | None = None) -> str:
        data = json.dumps({"message": message, "history": history or []}).encode()
        req = urllib.request.Request(
            CHAT_API_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
            return body.get("reply", "")

    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = App(token=SLACK_BOT_TOKEN)

    @app.event("app_mention")
    def handle_mention(event, say, client):
        text = event.get("text", "").strip()
        text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
        if not text:
            say("What can I help you with?")
            return
        try:
            reply = call_chat(text)
            say(reply)
        except Exception as e:
            logging.exception("Slack chat error")
            say(f"Something went wrong: {e}")

    @app.event("message")
    def handle_dm(event, say, client):
        if event.get("channel_type") != "im":
            return
        if event.get("subtype") or event.get("bot_id"):
            return
        text = event.get("text", "").strip()
        if not text:
            return
        try:
            reply = call_chat(text)
            say(reply)
        except Exception as e:
            logging.exception("Slack chat error")
            say(f"Something went wrong: {e}")

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    logging.info("BeccaBot Slack: starting (Socket Mode)")
    handler.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_slack_bot()
