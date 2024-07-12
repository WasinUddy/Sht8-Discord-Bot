import discord
from discord import app_commands
from discord.ext import commands
import re

class Team(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='create_team', description='Create a team')
    async def create_team(self, interaction: discord.Interaction, team_name: str):
        # Check if the user is already in a team
        self.bot.cursor.execute('SELECT * FROM teams WHERE %s = ANY(member_ids)', (interaction.user.id, ))
        if self.bot.cursor.fetchone():
            await interaction.response.send_message('You are already in a team. use /leave to leave your existing team', ephemeral=True)
            return
        
        # Check if the team name is already taken
        self.bot.cursor.execute('SELECT * FROM teams WHERE team_name = %s', (team_name, ))
        if self.bot.cursor.fetchone():
            await interaction.response.send_message('Team name is already taken.', ephemeral=True)
            return

        # Create the team
        self.bot.cursor.execute('INSERT INTO teams (team_name, member_ids) VALUES (%s, %s)', (team_name, [interaction.user.id]))
        self.bot.conn.commit()

        # Create the team role
        role = await interaction.guild.create_role(name=team_name)

        # Add the role to the user
        member = interaction.guild.get_member(interaction.user.id)
        await member.add_roles(role)

        await interaction.response.send_message(f'Team {team_name} created successfully.', ephemeral=True)

    
    @app_commands.command(name='join_team', description='Join a team')
    async def join_team(self, interaction: discord.Interaction, team_role: discord.Role):
        # Check if the user is already in a team
        self.bot.cursor.execute('SELECT * FROM teams WHERE %s = ANY(member_ids)', (interaction.user.id, ))
        if self.bot.cursor.fetchone():
            await interaction.response.send_message('You are already in a team. use /leave to leave your existing team', ephemeral=True)
            return

        # Check if the team exists
        self.bot.cursor.execute('SELECT * FROM teams WHERE team_name = %s', (team_role.name, ))
        team = self.bot.cursor.fetchone()
        if not team:
            await interaction.response.send_message('Team does not exist.', ephemeral=True)
            return

        # Add the user to the team
        member_ids = team['member_ids']
        member_ids.append(interaction.user.id)

        if len(member_ids) > 6:
            await interaction.response.send_message('Team is full.', ephemeral=True)
            return

        self.bot.cursor.execute('UPDATE teams SET member_ids = %s WHERE team_name = %s', (member_ids, team_role.name))
        self.bot.conn.commit()

        # Add the role to the user
        member = interaction.guild.get_member(interaction.user.id)
        await member.add_roles(team_role)

        await interaction.response.send_message(f'You have joined team {team_role.name}', ephemeral=True)


    @app_commands.command(name='leave_team', description='Leave a team')
    async def leave_team(self, interaction: discord.Interaction):
        # Check if the user is in a team
        self.bot.cursor.execute('SELECT * FROM teams WHERE %s = ANY(member_ids)', (interaction.user.id, ))
        team = self.bot.cursor.fetchone()
        if not team:
            await interaction.response.send_message('You are not in a team.', ephemeral=True)
            return

        # Remove the user from the team
        member_ids = team['member_ids']
        member_ids.remove(interaction.user.id)

        self.bot.cursor.execute('UPDATE teams SET member_ids = %s WHERE team_name = %s', (member_ids, team['team_name']))
        self.bot.conn.commit()

        # Remove the role from the user
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        role = discord.utils.get(guild.roles, name=team['team_name'])
        await member.remove_roles(role)

        await interaction.response.send_message('You have left the team.', ephemeral=True)
        