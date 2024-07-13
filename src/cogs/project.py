import discord
from discord import app_commands, ui
from discord.ext import commands
import re


class Project(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='submit', description='Submit a project')
    async def submit(self, interaction: discord.Interaction, project_name: str, project_url: str, project_description: str, thumbnail_url: str = ""):
        # None data is null
        if not project_name or not project_url or not project_description or not thumbnail_url:
            await interaction.response.send_message('Please provide all the required fields.', ephemeral=True)
            return

        # Check if the user is in a team
        self.bot.cursor.execute(
            'SELECT * FROM teams WHERE %s = ANY(member_ids)', (interaction.user.id, ))
        team = self.bot.cursor.fetchone()
        if not team:
            await interaction.response.send_message('You are not in a team. Create or join a team to submit a project.', ephemeral=True)
            return

        # Check if the project name is already taken
        self.bot.cursor.execute(
            'SELECT * FROM projects WHERE project_name = %s', (project_name, ))
        if self.bot.cursor.fetchone():
            await interaction.response.send_message('Project name is already taken.', ephemeral=True)
            return

        # Submit the project
        self.bot.cursor.execute('''
        INSERT INTO projects (team_name, project_name, project_url, project_description, thumbnail_url) 
        VALUES (%s, %s, %s, %s, %s) 
        ON CONFLICT (team_name) 
        DO UPDATE SET 
            project_name = EXCLUDED.project_name,
            project_url = EXCLUDED.project_url, 
            project_description = EXCLUDED.project_description, 
            thumbnail_url = EXCLUDED.thumbnail_url
        ''', (team['team_name'], project_name, project_url, project_description, thumbnail_url))
        self.bot.conn.commit()

        await interaction.response.send_message('Project submitted successfully.', ephemeral=True)

    @app_commands.command(name='set_github', description='Set your GitHub username')
    async def set_github(self, interaction: discord.Interaction, github_username: str):
        self.bot.cursor.execute('''
        INSERT INTO github (user_id, github_username)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET
            github_username = EXCLUDED.github_username
        ''', (interaction.user.id, github_username))
        self.bot.conn.commit()

        await interaction.response.send_message(f'GitHub Username successfully set to https://github.com/{github_username}', ephemeral=True)

    @app_commands.command(name='vote', description='Vote for a project')
    async def vote(self, interaction: discord.Interaction, team_role: discord.Role, rating: int):
        # Check if user is in any team
        self.bot.cursor.execute(
            'SELECT * FROM teams WHERE %s = ANY(member_ids)', (interaction.user.id, ))
        team = self.bot.cursor.fetchone()
        if not team:
            await interaction.response.send_message('You need to be in a team to vote!', ephemeral=True)
            return

        self.bot.cursor.execute('''
        INSERT INTO vote (user_id, team_name, rating)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, team_name)
        DO UPDATE SET
            rating = EXCLUDED.rating
        ''', (interaction.user.id, team_role.name, rating))
        self.bot.conn.commit()

        await interaction.response.send_message(f'Vote submitted', ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Project(bot))
