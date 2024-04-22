FROM python:3

MAINTAINER Charles Llewellyn "chllewel@cisco.com"

RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

# Expose port 5000
EXPOSE 5555

ENTRYPOINT ["python"]

CMD ["app.py"]
