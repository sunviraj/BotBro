FROM python:3.10

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential sqlite3

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Hugging Face Spaces run as user 1000, so we need to set permissions
RUN useradd -m -u 1000 user
RUN chown -R user:user /app
USER user

# Hugging Face expects the app to run on port 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
