FROM python:3.11.1

RUN apt-get update \
    && apt-get install iputils-ping -y

# Add pip requirements file
COPY requirements.txt /

# Install pip modules (slim image requires to pull and remove build dependencies)
RUN apt-get install -y --no-install-recommends gcc python-dev\
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt  \
    && apt-get purge -y --auto-remove gcc python-dev

# Add python script
COPY setup.py /
COPY slmClient.py /
COPY utils.py /

# Trigger Python script
CMD ["python", "-u", "./setup.py"]
