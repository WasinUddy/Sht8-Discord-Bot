import discord
from discord import app_commands, ui
from discord.ext import commands
import re

class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='assign_csv', description='Admin command to assign CSV file to initialize registration')
    async def assign_csv(self, interaction: discord.Interaction, attachment: discord.Attachment):
        # If caller is not admin, return
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You do not have permission to use this command.', ephemeral=True)
            return

        if not attachment.filename.endswith('.csv'):
            await interaction.response.send_message('Invalid file type. Please upload a CSV file.', ephemeral=True)
            return

        # Read the CSV file
        csv_data = await attachment.read()
        csv_data = csv_data.decode('utf-8')

        # Read only the first column of the CSV file
        reference_codes = [line.split(',')[0] for line in csv_data.split('\n') if line][1:]

        # Insert the reference codes into the database if they don't already exist
        for code in reference_codes:
            self.bot.cursor.execute(
                'INSERT INTO reference_codes (code) VALUES (%s) ON CONFLICT DO NOTHING',
                (code,)
            )
        self.bot.conn.commit()

        await interaction.response.send_message('Reference codes have been assigned successfully.', ephemeral=True)

    @app_commands.command(name='reset', description='Admin command to reset the database')
    async def reset(self, interaction: discord.Interaction):
        # If caller is not admin, return
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message('You do not have permission to use this command.', ephemeral=True)
            return

        # Reset the database
        self.bot.cursor.execute('DROP TABLE IF EXISTS registrations')
        self.bot.cursor.execute('DROP TABLE IF EXISTS reference_codes')
        self.bot.conn.commit()

        self.bot.initialize_database()

        await interaction.response.send_message('Database has been reset successfully.', ephemeral=True)

    @app_commands.command(name='register', description='Register with the provided reference code')
    async def register(self, interaction: discord.Interaction):
        class RegistrationForm(ui.Modal, title='ลงทะเบียน'):
            def __init__(self, bot, reference_codes):
                super().__init__()
                self.bot = bot
                self.reference_codes = reference_codes

            reference_code = ui.TextInput(
                label='Reference Code (รหัสอ้างอิง)',
                style=discord.TextStyle.short,
                placeholder='XXXXX',
                required=True
            )

            allergy = ui.TextInput(
                label='Food Allergy (อาการที่แพ้)',
                style=discord.TextStyle.short,
                placeholder='(Optional)',
                required=False
            )

            tshirt_size = ui.TextInput(
                label='T-Shirt Size (ขนาดเสื้อ)',
                style=discord.TextStyle.short,
                placeholder='(XS, S, M, L, XL, XXL, etc.)',
                required=True
            )

            single = ui.TextInput(
                label='Single or Taken (โสดหรือไม่)',
                style=discord.TextStyle.short,
                placeholder='Y/N (Optional)',
                required=False
            )

            async def on_submit(self, interaction: discord.Interaction):
                # Validate reference code
                if len(self.reference_code.value) != 6:
                    await interaction.response.send_message('Invalid reference code. It must be 6 characters.', ephemeral=True)
                    return

                # Check if the reference code exists in the database
                if self.reference_code.value.upper() not in self.reference_codes.keys():
                    await interaction.response.send_message('Invalid reference code. Please check your reference code and try again.', ephemeral=True)
                    return        
                
                if self.reference_codes[self.reference_code.value.upper()] == True:
                    await interaction.response.send_message('Reference code has already been used.', ephemeral=True)
                    return

                # Validate T-Shirt size (must be one of XS, S, M, L, XL, XXL, etc.)
                if not re.match(r'^(X*S|M|L|X*L)$', self.tshirt_size.value.upper()):
                    await interaction.response.send_message('Invalid T-Shirt size. It must be one of XS, S, M, L, XL, XXL, etc.', ephemeral=True)
                    return

                # Validate single or taken (must be Y or N)
                single_value = None
                if self.single.value:
                    if not re.match(r'^[YN]$', self.single.value.upper()):
                        await interaction.response.send_message('Invalid value for Single or Taken. It must be Y or N.', ephemeral=True)
                        return
                    single_value = self.single.value.upper() == 'Y'

                # Insert the form data into the database
                self.bot.cursor.execute(
                    '''INSERT INTO registrations (user_id, reference_code, allergy, tshirt_size, single) 
                       VALUES (%s, %s, %s, %s, %s)''',
                    (interaction.user.id, self.reference_code.value.upper(), self.allergy.value or None, self.tshirt_size.value.upper(), single_value)
                )

                self.bot.cursor.execute(
                    'UPDATE reference_codes SET used = TRUE WHERE code = %s',
                    (self.reference_code.value.upper(),)
                )

                self.bot.conn.commit()
                
                await interaction.response.send_message('ลงทะเบียนสำเร็จแล้ว', ephemeral=True)

                # Assign role to the user
                guild = self.bot.get_guild(interaction.guild.id)

                role = discord.utils.get(guild.roles, name='onsite participant')

                await interaction.user.add_roles(role)




        # Fetch all reference codes from the database
        self.bot.cursor.execute('SELECT * FROM reference_codes')
        reference_codes = {row['code']:row['used'] for row in self.bot.cursor.fetchall()}

        form = RegistrationForm(self.bot, reference_codes)
        await interaction.response.send_modal(form)

async def setup(bot: commands.Bot):
    await bot.add_cog(Registration(bot))
