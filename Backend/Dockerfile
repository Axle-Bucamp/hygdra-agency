# Use python 3.11 image
FROM python:3.11-slim

# Set working directory
COPY app /app
WORKDIR /app

# Install dependencies
RUN apt update && apt install -y python3-pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install .
# Expose the port that Uvicorn will run on
EXPOSE 7060

# Command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7060"]
