FROM python:3

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

COPY . .

COPY wait_for_monerod.py .

EXPOSE 5000 18081

CMD ["sh", "-c", "python wait_for_monerod.py && python quickseed.py"]