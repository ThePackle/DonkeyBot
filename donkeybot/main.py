import logging
import os
import time
from typing import TypeVar

import discord
import sentry_sdk
from discord import Intents
from discord.ext import commands

from donkeybot.helpers.config_helper import (
    DISCORD_KEY,
    ENV,
    GUILD_ID,
    ROLES_LIST,
    SENTRY_SDN,
)
from donkeybot.helpers.embed_helper import EmbedCreator
from donkeybot.helpers.setup_json import setup_json
from donkeybot.helpers.setup_logging import setup_logging

T = TypeVar("T")


class BotContext(EmbedCreator, commands.Context):
    bot: "DonkeyBot"


class DonkeyBot(commands.Bot):
    def __init__(self, **kwargs):
        setup_logging()
        setup_json()

        intent = Intents.default()
        intent.message_content = True
        intent.reactions = True
        intent.members = True
        intent.guilds = True

        self._log = logging.getLogger("DonkeyBot")
        self.case_insensitive = True
        self.start_time = time.time()

        self.roles: dict[dict, str] = ROLES_LIST[ENV]
        self._log.info("Bot successfully started...")

        if ENV == "primary":
            sentry_sdk.init(
                dsn=SENTRY_SDN,
                send_default_pii=True,
                traces_sample_rate=1.0,
            )
        else:
            self._log.info("Currently in dev mode; skipping Sentry...")

        super().__init__(
            command_prefix="/", intents=intent, case_insensitive=True, **kwargs
        )

    async def setup_hook(self) -> None:
        """Loads modules after loading the bot."""
        self._log.info("setup_hook initialized...")

        self.tree.clear_commands(guild=discord.Object(id=GUILD_ID))

        self.base = BaseCommands(self)
        await self.add_cog(self.base)

        modules_dir = os.path.join(os.path.dirname(__file__), "modules")
        for file in os.listdir(modules_dir):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]
                try:
                    await self.load_extension(f"donkeybot.modules.{module_name}")
                    self._log.info(f"Loaded module {module_name}")
                except commands.ExtensionError as e:
                    self._log.error(f"Failed to load module {module_name}", exc_info=e)

        await self.tree.sync(guild=discord.Object(id=GUILD_ID))


class BaseCommands(commands.Cog):
    def __init__(self, bot: DonkeyBot) -> None:
        self.bot = bot


def main():
    bot = DonkeyBot()
    bot.run(DISCORD_KEY)


if __name__ == "__main__":
    main()
