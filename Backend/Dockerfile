# Use python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy the requirements.txt and install dependencies
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the application code
COPY app /app

# Expose the port that Uvicorn will run on
EXPOSE 7060

# Command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7060"]
