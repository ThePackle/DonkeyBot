import time
from datetime import datetime
from typing import TYPE_CHECKING, TypedDict, cast
from zoneinfo import ZoneInfo

import discord
import sentry_sdk
from discord.ext import tasks
from discord.ext.commands import Cog
from twitchAPI.helper import first
from twitchAPI.twitch import Twitch
from twitchAPI.type import SortMethod, VideoType

from donkeybot.helpers.config_helper import (
    LIVE_LIST,
    STREAM_CHANNEL,
    STREAM_OFF_THREAD,
    STREAMER,
    TTV_ID,
    TTV_SCHEDULE_END,
    TTV_SCHEDULE_START,
    TTV_TIMEOUT,
    TTV_TOKEN,
)
from donkeybot.helpers.embed_helper import EmbedCreator
from donkeybot.helpers.json_helper import JsonHelper

if TYPE_CHECKING:
    from donkeybot.main import DonkeyBot


class LiveStream(TypedDict):
    user_id: str
    embed: int
    role: int
    game: str
    thumbnail: str
    pfp: str | None
    check: int


async def setup(bot: "DonkeyBot"):
    await bot.add_cog(StreamingCog(bot))


async def teardown(bot: "DonkeyBot"):
    await bot.remove_cog("Streaming")


class StreamingCog(
    Cog, name="Streaming", description="Manages DonkeyBot's stream checks"
):
    def __init__(self, bot: "DonkeyBot") -> None:
        self.bot = bot
        self.stream_role: int = int(self.bot.roles["admin"]["stream"])
        self.live: dict[str, LiveStream] = cast(dict[str, LiveStream], LIVE_LIST)
        self.stream_channel: discord.TextChannel
        self.stream_thread: discord.TextChannel

    async def cog_load(self) -> None:
        self.stream_channel = cast(
            discord.TextChannel,
            await self.bot.fetch_channel(STREAM_CHANNEL),
        )
        self.stream_thread = cast(
            discord.TextChannel,
            await self.bot.fetch_channel(STREAM_OFF_THREAD),
        )
        self.ttv_client = await Twitch(app_id=TTV_ID, app_secret=TTV_TOKEN)

        self.stream_loop.start()

    async def cog_unload(self) -> None:
        await self.ttv_client.close()

        self.stream_loop.cancel()

    def _in_schedule(
        self,
    ) -> bool:
        eastern_hour = datetime.now(ZoneInfo("America/New_York")).hour
        return TTV_SCHEDULE_START <= eastern_hour < TTV_SCHEDULE_END

    @tasks.loop(minutes=1)
    async def stream_loop(self) -> None:
        if not self._in_schedule() and not self.live:
            return

        try:
            stream = await first(self.ttv_client.get_streams(user_login=[STREAMER]))
            self.bot._log.info(f"Stream check for '{STREAMER}': {stream}")

            if stream:
                user = await first(self.ttv_client.get_users(logins=[STREAMER]))
                try:
                    self.live[stream.user_name]
                except (KeyError, TypeError):
                    if user:
                        thumbnail = stream.thumbnail_url.replace(
                            "{width}", "1280"
                        ).replace("{height}", "720")

                        e_thumbnail = thumbnail + "?rand=" + str(int(time.time()))

                        embed_stream = await self.stream_channel.send(
                            embed=EmbedCreator.twitch_embed(
                                title=stream.title,
                                stream_name=stream.user_name,
                                stream_game=stream.game_name,
                                viewer_count=stream.viewer_count,
                                twitch_pfp=(
                                    user.profile_image_url
                                    if user and user.profile_image_url
                                    else None
                                ),
                                thumbnail=e_thumbnail,
                            )
                        )
                        role_msg = await self.stream_channel.send(
                            f"<@&{self.stream_role}>"
                        )

                        self.live.update(
                            {
                                f"{stream.user_name}": {
                                    "user_id": user.id,
                                    "embed": embed_stream.id,
                                    "role": role_msg.id,
                                    "game": stream.game_name,
                                    "thumbnail": thumbnail,
                                    "pfp": (
                                        user.profile_image_url
                                        if user and user.profile_image_url
                                        else None
                                    ),
                                    "check": 0,
                                }
                            }
                        )

            remove_stream = []
            for user, messages in self.live.items():
                if stream is None:
                    if messages["check"] >= TTV_TIMEOUT:
                        archive = await first(
                            self.ttv_client.get_videos(
                                user_id=messages["user_id"],
                                video_type=VideoType.ARCHIVE,
                                first=1,
                                sort=SortMethod.TIME,
                            )
                        )

                        if archive:
                            await self.stream_thread.send(
                                embed=EmbedCreator.twitch_offline_embed(
                                    stream_name=user,
                                    stream_game=messages["game"],
                                    twitch_pfp=messages["pfp"],
                                    archive_video=archive.url,
                                )
                            )

                        remove_embed = await self.stream_channel.fetch_message(
                            messages["embed"]
                        )
                        remove_role = await self.stream_channel.fetch_message(
                            messages["role"]
                        )

                        await remove_embed.delete()
                        await remove_role.delete()

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

            for user in remove_stream:
                self.live.pop(user, None)

            JsonHelper.save_json(self.live, "json/live.json")
        except Exception as error:
            self.bot._log.exception("EXCEPTION:", exc_info=error)
            sentry_sdk.capture_exception(error)
