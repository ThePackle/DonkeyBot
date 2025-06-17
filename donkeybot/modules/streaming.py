import asyncio
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks
from discord.ext.commands import Cog
from twitchAPI.helper import first
from twitchAPI.twitch import Twitch
from twitchAPI.type import SortMethod, VideoType

from donkeybot.helpers.config_helper import (
    LIVE_LIST,
    STREAM_CHANNEL,
    STREAM_OFF_THREAD,
    TTV_ID,
    TTV_TOKEN,
)
from donkeybot.helpers.embed_helper import EmbedCreator
from donkeybot.helpers.json_helper import JsonHelper

if TYPE_CHECKING:
    from main import DonkeyBot


async def setup(bot: "DonkeyBot"):
    await bot.add_cog(StreamingCog(bot))


async def teardown(bot: "DonkeyBot"):
    await bot.remove_cog(name="Streaming")


class StreamingCog(
    Cog, name="Streaming", description="Manages DonkeyBot's stream checks"
):
    def __init__(self, bot: "DonkeyBot") -> None:
        self.bot = bot
        self.stream_role: int = int(self.bot.roles["admin"]["stream"])
        self.live: dict[dict, str] = LIVE_LIST
        self.task_lock = asyncio.Lock()

    async def cog_load(self) -> None:
        self.stream_channel = await self.bot.fetch_channel(STREAM_CHANNEL)
        self.stream_thread = await self.bot.fetch_channel(STREAM_OFF_THREAD)
        self.ttv_client = await Twitch(app_id=TTV_ID, app_secret=TTV_TOKEN)

        self.stream_loop.start()

    async def cog_unload(self) -> None:
        await self.ttv_client.close()

        self.stream_loop.cancel()

    @tasks.loop(minutes=1)
    async def stream_loop(self) -> None:
        """Checks livestream status of players every minute."""
        async with self.task_lock:
            stream = await first(self.ttv_client.get_streams(user_login="ThreeAlpaca"))
            if not stream:
                return

            user = await first(self.ttv_client.get_users(logins="ThreeAlpaca"))
            try:
                self.live[stream.user_name]
            except (KeyError, TypeError):
                thumbnail = stream.thumbnail_url.replace("{width}", "1280").replace(
                    "{height}", "720"
                )

                e_thumbnail = thumbnail + "?rand=" + str(int(time.time()))

                embed_stream = await self.stream_channel.send(
                    embed=EmbedCreator.twitch_embed(
                        title=stream.title,
                        stream_name=stream.user_name,
                        stream_game=stream.game_name,
                        viewer_count=stream.viewer_count,
                        twitch_pfp=user.profile_image_url,
                        thumbnail=e_thumbnail,
                    )
                )
                role_msg = await self.stream_channel.send(f"<@&{self.stream_role}>")

                self.live.update(
                    {
                        f"{stream.user_name}": {
                            "user_id": user.id,
                            "embed": embed_stream.id,
                            "role": role_msg.id,
                            "game": stream.game_name,
                            "thumbnail": thumbnail,
                            "pfp": user.profile_image_url,
                            "check": 0,
                        }
                    }
                )

            remove_stream = []
            for user, messages in self.live.items():

                stream = await first(self.ttv_client.get_streams(user_login=user))

                if stream is None:
                    if messages["check"] >= 5:
                        remove_stream.append(user)
                    else:
                        check = messages["check"] + 1
                        self.live[user].update({"check": check})
                else:
                    e_thumbnail = (
                        messages["thumbnail"] + "?rand=" + str(int(time.time()))
                    )

                    embed = EmbedCreator.twitch_embed(
                        title=stream.title,
                        stream_name=user,
                        stream_game=stream.game_name,
                        viewer_count=stream.viewer_count,
                        twitch_pfp=messages["pfp"],
                        thumbnail=e_thumbnail,
                    )

                    try:
                        embed_stream = await self.stream_channel.fetch_message(
                            messages["embed"]
                        )

                        await embed_stream.edit(embed=embed)
                    except discord.errors.NotFound:
                        new_embed = await self.stream_channel.send(embed=embed)
                        self.live[user].update({"embed": new_embed.id})

                    self.live[user].update({"check": 0})

            if len(remove_stream) > 0:
                for stream in remove_stream:
                    archive = await first(
                        self.ttv_client.get_videos(
                            user_id=self.live[stream]["user_id"],
                            video_type=VideoType.ARCHIVE,
                            first=1,
                            sort=SortMethod.TIME,
                        )
                    )

                    await self.stream_thread.send(
                        embed=EmbedCreator.twitch_offline_embed(
                            stream_name=stream,
                            stream_game=self.live[stream]["game"],
                            twitch_pfp=self.live[stream]["pfp"],
                            archive_video=archive.url,
                        )
                    )

                    remove_embed = await self.stream_channel.fetch_message(
                        self.live[stream]["embed"]
                    )
                    remove_role = await self.stream_channel.fetch_message(
                        self.live[stream]["role"]
                    )

                    await remove_embed.delete()
                    await remove_role.delete()
                    self.live.pop(stream, None)

            JsonHelper.save_json(self.live, "json/live.json")
