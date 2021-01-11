FROM python:3.8
WORKDIR /app
ADD . /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopencv-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --trusted-host pypi.python.org -r requirements.txt
EXPOSE 5000
CMD ["python", "app.py"]