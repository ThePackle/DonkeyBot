import asyncio
from typing import TYPE_CHECKING, Any

import discord
from discord import Interaction, TextChannel, app_commands
from discord.ext.commands import Cog

from donkeybot.helpers.config_helper import ENV, GUILD_ID, REACTIONS_LIST
from donkeybot.helpers.json_helper import JsonHelper

if TYPE_CHECKING:
    from donkeybot.main import DonkeyBot


async def setup(bot: "DonkeyBot") -> None:
    await bot.add_cog(RoleCog(bot))


async def teardown(bot: "DonkeyBot") -> None:
    await bot.remove_cog("Roles")


class RoleCog(Cog, name="Roles", description="Manages DonkeyBot's reaction messages."):
    def __init__(self, bot: "DonkeyBot") -> None:
        self.bot = bot
        self.reactions_list: dict[str, dict[str, Any]] = REACTIONS_LIST[ENV]

    async def cog_load(self) -> None:
        self.bot.tree.add_command(
            self.reaction_group,
            guild=discord.Object(id=GUILD_ID),
            override=True,
        )

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            self.reaction_group.name,
            guild=discord.Object(id=GUILD_ID),
        )

    ###########################################################################
    # reaction_group Commands
    ###########################################################################
    reaction_group = app_commands.Group(
        name="reaction", description="Modify how roles are assigned."
    )

    @reaction_group.command(
        name="message",
        description="Set or removes reactions and roles from a specific message.",
    )
    @app_commands.describe(
        action="Set or remove the reaction from the message ID given",
        message="Message that will receive the emoji reaction.",
        emoji="Emoticon that will be used to represent a role as a recaction.",
        role="@Discord Role you want to use associated with the emoticon.",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="set", value="set"),
            app_commands.Choice(name="remove", value="remove"),
        ]
    )
    async def reactions(
        self,
        interaction: Interaction,
        action: app_commands.Choice[str],
        message: str,
        emoji: str | None = None,
        role: discord.Role | None = None,
    ) -> None:
        """Set or removes reactions and roles from a specific message."""
        channel = interaction.channel
        if not isinstance(channel, TextChannel):
            await interaction.response.send_message(
                "This command can only be used in a text channel.",
                ephemeral=True,
            )
            return

        if action.value == "set":
            if not emoji or not role:
                await interaction.response.send_message(
                    "The emoji and role parameters are required to set a reaction.",
                    ephemeral=True,
                )
                return

            message_obj = await channel.fetch_message(int(message))
            await message_obj.add_reaction(emoji)

            if message not in self.reactions_list:
                self.reactions_list[message] = {"reactions": {}}

            self.reactions_list[message]["reactions"][emoji] = role.id
            REACTIONS_LIST[ENV] = self.reactions_list

            JsonHelper.save_json(REACTIONS_LIST, "json/reactions.json")

            await interaction.response.send_message(
                f"{message} has received {emoji} as a reaction; when pressed, it will give {role}!",
                ephemeral=True,
            )
        else:
            try:
                message_obj = await channel.fetch_message(int(message))

                if emoji or role:
                    if emoji:
                        await message_obj.clear_reaction(emoji)

                    if role:
                        found_emoji: str | None = None
                        for emoji_find, role_id in self.reactions_list[message][
                            "reactions"
                        ].items():
                            if role_id == role.id:
                                found_emoji = emoji_find
                                await message_obj.clear_reaction(found_emoji)
                                break

                        if found_emoji is None:
                            await interaction.response.send_message(
                                "Role not found in reactions list.", ephemeral=True
                            )
                            return
                        emoji = found_emoji

                    self.reactions_list[message]["reactions"].pop(emoji, None)
                    if len(self.reactions_list[message]["reactions"]) == 0:
                        self.reactions_list.pop(message, None)
                else:
                    for reaction_emoji in self.reactions_list[message][
                        "reactions"
                    ].keys():
                        await message_obj.clear_reaction(reaction_emoji)

                    self.reactions_list.pop(message, None)

                REACTIONS_LIST[ENV] = self.reactions_list
                JsonHelper.save_json(REACTIONS_LIST, "json/reactions.json")

                await interaction.response.send_message(
                    f"{message} successfully modified!", ephemeral=True
                )
            except (KeyError, TypeError) as e:
                await interaction.response.send_message(
                    f"Message ID {message} was not in the reactions list or an error occurred.",
                    ephemeral=True,
                )
                self.bot._log.exception("REACTION_REMOVE_EXCEPTION", exc_info=e)

    ###########################################################################
    # Listeners
    ###########################################################################

    @Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        channel = guild.get_channel(payload.channel_id)
        if not isinstance(channel, TextChannel):
            return

        message = await channel.fetch_message(payload.message_id)

        emoji_str = str(payload.emoji)
        message_str = str(payload.message_id)

        if message_str not in self.reactions_list:
            return

        role_id = self.reactions_list[message_str]["reactions"].get(emoji_str)
        if role_id is None:
            await message.clear_reaction(payload.emoji)
            return

        role = guild.get_role(role_id)
        if not role:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            member = await guild.fetch_member(payload.user_id)

        if member.bot or (self.bot.user is not None and member.id == self.bot.user.id):
            return

        if role in member.roles:
            await member.remove_roles(role)
            await member.send(
                f"{role.name} role was removed from your profile successfully in {guild.name}."
            )
            await asyncio.sleep(0.5)
        else:
            await member.add_roles(role)
            await member.send(
                f"{role.name} role was added to your profile successfully in {guild.name}."
            )
            await asyncio.sleep(0.5)

        await message.remove_reaction(payload.emoji, member)
        await message.add_reaction(payload.emoji)

    @Cog.listener()
    async def on_raw_reaction_clear(
        self, payload: discord.RawReactionClearEvent
    ) -> None:
        message_id = str(payload.message_id)
        if message_id in self.reactions_list:
            self.bot._log.warning(
                f"Someone cleared all reactions from {payload.message_id}. Readding reactions..."
            )

            if payload.guild_id is None:
                return

            guild = self.bot.get_guild(payload.guild_id)
            if guild is None:
                return

            channel = guild.get_channel(payload.channel_id)
            if not isinstance(channel, TextChannel):
                return

            message = await channel.fetch_message(payload.message_id)
            await message.clear_reactions()

            for reaction in self.reactions_list[message_id]["reactions"].keys():
                await message.add_reaction(reaction)
