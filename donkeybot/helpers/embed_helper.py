import random
from datetime import datetime, timezone

from discord import Embed
from dotenv import load_dotenv

from donkeybot.helpers.config_helper import BOT

load_dotenv()


class EmbedCreator:
    @staticmethod
    def twitch_embed(
        title: str,
        stream_name: str,
        stream_game: str,
        viewer_count: int,
        twitch_pfp: str,
        thumbnail: str,
    ) -> Embed:
        """This embed is used to display currently online livestreams."""
        embed = Embed(
            title=title,
            url=f"https://twitch.tv/{stream_name}",
            color=random.randint(0, 0xFFFFFF),
            timestamp=datetime.now(timezone.utc),
        )

        embed.set_author(
            name=f"{stream_name} is now live!",
            url=f"https://twitch.tv/{stream_name}",
            icon_url=twitch_pfp,
        )
        embed.add_field(name="Game", value=stream_game, inline=True)
        embed.add_field(name="Viewers", value=viewer_count, inline=True)
        embed.set_image(url=thumbnail)
        embed.set_footer(text=BOT)

        return embed

    @staticmethod
    def twitch_offline_embed(
        stream_name: str,
        stream_game: str,
        twitch_pfp: str | None,
        archive_video: str | None,
    ) -> Embed:
        """This embed is used to display currently online livestreams."""
        embed = Embed(
            title=f"{stream_name} is offline!",
            url=f"https://twitch.tv/{stream_name}",
            color=random.randint(0, 0xFFFFFF),
            timestamp=datetime.now(timezone.utc),
        )

        embed.set_author(
            name=stream_name,
            url=f"https://twitch.tv/{stream_name}",
            icon_url=twitch_pfp,
        )
        embed.add_field(name="Game", value=stream_game, inline=True)

        if archive_video:
            embed.description = f"Stream VOD: {archive_video}"

        embed.set_footer(text=BOT)

        return embed
