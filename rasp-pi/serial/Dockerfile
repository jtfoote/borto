FROM python:3.11-slim
WORKDIR /app
COPY serial/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY serial/ .
CMD ["python", "serial_reader.py"]
