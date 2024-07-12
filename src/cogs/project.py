import discord
from discord import app_commands, ui
from discord.ext import commands
import re

class Project(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='submit', description='Submit a project')
    async def submit(self, interaction: discord.Interaction, project_name: str, project_url: str, project_description: str, thumbnail_url: str):
        # None data is null
        if not project_name or not project_url or not project_description or not thumbnail_url:
            await interaction.response.send_message('Please provide all the required fields.', ephemeral=True)
            return

        # Check if the user is in a team
        self.bot.cursor.execute('SELECT * FROM teams WHERE %s = ANY(member_ids)', (interaction.user.id, ))
        team = self.bot.cursor.fetchone()
        if not team:
            await interaction.response.send_message('You are not in a team. Create or join a team to submit a project.', ephemeral=True)
            return

        # Check if the project name is already taken
        self.bot.cursor.execute('SELECT * FROM projects WHERE project_name = %s', (project_name, ))
        if self.bot.cursor.fetchone():
            await interaction.response.send_message('Project name is already taken.', ephemeral=True)
            return

        # Submit the project
        self.bot.cursor.execute('''
        INSERT INTO projects (team_name, project_name, project_url, project_description, thumbnail_url) 
        VALUES (%s, %s, %s, %s, %s) 
        ON CONFLICT (team_name, project_name) 
        DO UPDATE SET 
            project_url = EXCLUDED.project_url, 
            project_description = EXCLUDED.project_description, 
            thumbnail_url = EXCLUDED.thumbnail_url
        ''', (team['team_name'], project_name, project_url, project_description, thumbnail_url))
        self.bot.conn.commit()

        await interaction.response.send_message('Project submitted successfully.', ephemeral=True)
    

async def setup(bot: commands.Bot):
    await bot.add_cog(Project(bot))
