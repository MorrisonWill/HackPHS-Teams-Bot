# Written by Will Morrison

import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# Getting the token from an environment file so you don't steal it
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# Creating the bot with the prefix !
bot = commands.Bot(command_prefix='!')

# Removing the help command so I can rewrite it later
bot.remove_command('help')


# Function to be used later to check if people reply with yes or no
def check(m):
    return m.content == 'yes' or m.content == 'no'


def get_mentor_role(ctx):
    for role in ctx.guild.roles:
        if role.name == 'mentor':
            return role

def team_name(user: discord.User):
    return f'{user.name.replace(" ", "-").lower()}-team'

# Logging when the bot is ready and setting the playing text to !help
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='!help'))
    print('Ready to manage teams.')


# Simple help command that DMs an embed to the user
@bot.command()
async def help(ctx):
    embed = discord.Embed(color=0x00ff00)
    embed.add_field(name='!help', value='This command. Shows all other commands.', inline=False)
    embed.add_field(name='!create <yourself> <member1> <member2> <member3>', value='Creates a team and asks other '
                                                                                   'members for confirmation.',
                    inline=False)
    embed.add_field(name='!add <member>', value='Add a member to your team after creation. Asks them for '
                                                'confirmation.',
                    inline=False)
    embed.add_field(name='!code', value='View the code for this bot.', inline=False)
    embed.set_author(name='Welcome to the hackathon!')
    await ctx.message.author.send(embed=embed)


@bot.command()
async def code(ctx):
    await ctx.message.author.send('https://gitlab.com/WillMorrison/hackphs-teams-bot')


# Main function that creates a team
@bot.command()
async def create(ctx, *args: discord.User):
    # Identify the sender
    sender = ctx.message.author
    # Finding the mentor role object
    mentor_role = get_mentor_role(ctx)
    # Permissions for the channels that will be created
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
    }


    # Finally, check to see if they have already created a team
    if discord.utils.get(ctx.guild.text_channels, name=team_name(sender)) is not None:
        await ctx.send('You have already created a team.')
        return
    category = discord.utils.get(ctx.guild.categories, name='TEAMS')

    text_channel = await ctx.guild.create_text_channel(team_name(sender), category=category, overwrites=overwrites)
    voice_channel = await ctx.guild.create_voice_channel(team_name(sender), category=category, overwrites=overwrites)

    # Adding organizers to the channels
    await text_channel.set_permissions(mentor_role, read_messages=True, send_messages=True, read_message_history=True)
    await voice_channel.set_permissions(mentor_role, read_messages=True, send_messages=False)

    await text_channel.set_permissions(sender, read_messages=True, send_messages=True, read_message_history=True)
    await voice_channel.set_permissions(sender, read_messages=True, send_messages=False)

    await ctx.send('Created your team and added you to it.')
    # Skip to the next user

    # For each possible team member, send them a DM and wait for them to say yes
    for user in args:
        if user == sender: continue
        # Waiting for them to say yes or no or timeout in 60 seconds
        try:
            # Ask the user if they want to join the team
            await user.send(f'{sender} has invited you to join his team. Do you accept the invitation? (yes/no)')
            msg = await bot.wait_for('message', timeout=60.0, check=check)
            if msg.content == 'yes':
                await text_channel.set_permissions(user, read_messages=True, send_messages=True, read_message_history=True)
                await voice_channel.set_permissions(user, read_messages=True, send_messages=False)
            else: await msg.author.send('Not added to the group.')
        except asyncio.TimeoutError:
            await user.send('You were too slow. Please ask your other team member to !add you to the team channel.')




# Function to add additional members to the team.
# Known problem that it is possible to add beyond four members.
# It is possible to fix but I think it would require adding a database to store teams.
@bot.command()
async def add(ctx, user: discord.User):
    # Identify the sender
    sender = ctx.message.author

    # Make sure they have a team
    if discord.utils.get(ctx.guild.text_channels, name=team_name(sender)) is None:
        await sender.send('You do not have a group yet. Use !create to make one.')
        return

    # Find the text channel and voice channel
    text_channel = discord.utils.get(ctx.guild.text_channels, name=team_name(sender))
    voice_channel = discord.utils.get(ctx.guild.voice_channels, name=team_name(sender))

    # Send the invitation to the user
    to_send = f'{sender} has invited you to join his team. Do you accept the invitation? (yes/no)'
    await user.send(to_send)

    # Waiting for them to say yes or no or timeout in 60 seconds
    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await user.send('You were too slow. Please ask your other team member to !add you to the team channel.')
        return

    # If they say yes, add them to the text and voice channel
    if msg.content == 'yes':
        await text_channel.set_permissions(user, read_messages=True, send_messages=True, read_message_history=True)
        await voice_channel.set_permissions(user, read_messages=True, send_messages=False)
    # Otherwise, say they weren't added to the group
    elif msg.content == 'no':
        await msg.author.send('Not added to the group.')


bot.run(token)
