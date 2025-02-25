FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPy . .

EXPOSE 28088 18081

CMD ["python", "quickseed.py"]