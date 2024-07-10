FROM python:3.12-slim

# Set the working directory
WORKDIR /app

COPY . .

# Install the dependencies
RUN pip install -r requirements.txt

# Change Directory
WORKDIR /app/src

# Run the application
CMD ["python", "bot.py"]