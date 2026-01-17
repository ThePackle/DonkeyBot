from typing import TYPE_CHECKING

from discord import Interaction, Member
from discord.app_commands import CheckFailure, check

if TYPE_CHECKING:
    from donkeybot.main import DonkeyBot


def is_admin():
    """Restricts commands to requiring to be in an admin or moderator role. Use for sub-commands."""

    @check
    async def predicate(interaction: Interaction) -> bool:
        bot: "DonkeyBot" = interaction.client  # type: ignore[assignment]
        guild = interaction.guild
        if guild is None:
            raise CheckFailure()

        if interaction.user == guild.owner:
            return True

        member = guild.get_member(interaction.user.id)
        if member is None:
            raise CheckFailure()

        for role in member.roles:
            if role.id in list(bot.roles.get("admin", {}).values()):
                return True

        raise CheckFailure()

    return predicate


async def is_admin_user(user: Member, bot: "DonkeyBot") -> bool:
    """Returns True if the user is the owner or has an admin/mod role."""
    if user.guild.owner is not None and user == user.guild.owner:
        return True

    for role in user.roles:
        if role.id in list(bot.roles.get("admin", {}).values()):
            return True

    return False
