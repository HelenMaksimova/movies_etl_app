FROM python:3.12

WORKDIR /opt/app

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY manage.py .
COPY src ./src

ENTRYPOINT ["python", "manage.py"]