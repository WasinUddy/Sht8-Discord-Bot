import discord
from discord.ext import commands
import os
import sys
import traceback
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
GUILD_ID = os.getenv('GUILD_ID')

initial_extensions = [f'cogs.{c[:-3]}' for c in os.listdir('cogs') if c.endswith('.py')]

class Bot(commands.Bot):
    def __init__(self, testing_guild_id=None):
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=discord.Intents.all())

        # Connect to PostgreSQL database using the connection string
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.initialize_database()
        self.testing_guild_id = testing_guild_id

    def initialize_database(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            reference_code TEXT NOT NULL,
            allergy TEXT,
            tshirt_size TEXT NOT NULL,
            single BOOLEAN
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS reference_codes (
            code TEXT PRIMARY KEY,
            used BOOLEAN DEFAULT FALSE
        )                 
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            team_name TEXT PRIMARY KEY,
            member_ids BIGINT[] NOT NULL
        )
        ''')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            team_name TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            project_url TEXT NOT NULL,
            project_description TEXT NOT NULL,
            thumbnail_url TEXT NOT NULL
        )
        ''')

        self.conn.commit()


    async def setup_hook(self):
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

        # Syncing the commands with the testing guild
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            try: 
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            except discord.errors.Forbidden as e:
                logging.error("Bot does not have permissions to sync commands in the testing guild.")
                logging.warning(e)

    async def on_ready(self):
        print("Bot is ready.")

if __name__ == "__main__":
    bot = Bot(testing_guild_id=GUILD_ID)

    @bot.command()
    @commands.is_owner()
    async def sync(ctx):
        await bot.tree.sync()
        await ctx.send("Commands synced successfully.")

    bot.run(DISCORD_TOKEN)
