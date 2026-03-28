import os

from dotenv import load_dotenv

from donkeybot.helpers.json_helper import JsonHelper

load_dotenv()

ENV: str = "primary" if os.getenv("DEBUG") == "False" else "dev"

CHANNELS_LIST: dict[str, dict] = JsonHelper.load_json("json/channels.json")
LIVE_LIST: dict[str, dict] = JsonHelper.load_json("json/live.json")
REACTIONS_LIST: dict[str, dict] = JsonHelper.load_json("json/reactions.json")
REMINDER_LIST: dict[str, dict] = JsonHelper.load_json("json/reminders.json")
ROLES_LIST: dict[str, dict] = JsonHelper.load_json("json/roles.json")
STATUSES_LIST: list[str] = JsonHelper.load_json("json/statuses.json")

GUILD_ID: int = int(CHANNELS_LIST[ENV]["server"])
STREAM_CHANNEL: int = int(CHANNELS_LIST[ENV]["stream"]["main"])
STREAM_OFF_THREAD: int = int(CHANNELS_LIST[ENV]["stream"]["thread"])

SENTRY_SDK: str = os.getenv("SENTRY_SDK", "")

TTV_TOKEN: str = os.getenv("TWITCH_TOKEN", "")
TTV_ID: str = os.getenv("TWITCH_ID", "")
TTV_TIMEOUT: int = int(os.getenv("TTV_TIMEOUT", "5"))
TTV_SCHEDULE_START: int = int(os.getenv("TTV_SCHEDULE_START", "13"))
TTV_SCHEDULE_END: int = int(os.getenv("TTV_SCHEDULE_END", "21"))

BOT: str = os.getenv("BOT_NAME", "DonkeyBot")

STREAMER: str = os.getenv("STREAMER", "ThreeAlpaca")

DISCORD_KEY: str = (
    os.getenv("DISCORD_PRIMARY_KEY", "")
    if os.getenv("DEBUG") == "False"
    else os.getenv("DISCORD_BETA_KEY", "")
)
