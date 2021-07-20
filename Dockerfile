FROM python:3.7.10-slim
LABEL MAINTAINER="dcueng@godaddy.com"

RUN addgroup dcu && adduser --disabled-password --disabled-login --no-create-home --ingroup dcu --system dcu

# Expose Flask port 5000
EXPOSE 5000

COPY ./*.ini ./*.py ./runserver.sh /app/
COPY . /tmp

RUN apt-get update && apt-get install gcc -y
RUN PIP_CONFIG_FILE=/tmp/pip_config/pip.conf pip install --compile /tmp
RUN apt-get remove -y gcc

# cleanup
RUN rm -rf /tmp

WORKDIR /app

ENTRYPOINT ["/app/runserver.sh"]