FROM gdartifactory1.jfrog.io/docker-dcu-local/dcu-python3.11:1.1
LABEL MAINTAINER="dcueng@godaddy.com"

USER root
RUN apt-get update && apt-get install gcc -y

# Expose Flask port 5000
EXPOSE 5000

RUN mkdir -p /tmp/build
COPY requirements.txt /tmp/build/
COPY pip_config /tmp/build/pip_config
RUN PIP_CONFIG_FILE=/tmp/build/pip_config/pip.conf pip install -r /tmp/build/requirements.txt

COPY *.py /tmp/build/
COPY test_requirements.txt /tmp/build/
COPY README.md /tmp/build/
COPY service /tmp/build/service
# pip install private pips staged by Makefile
RUN PIP_CONFIG_FILE=/tmp/build/pip_config/pip.conf pip install --compile /tmp/build/

COPY ./*.ini ./*.py ./runserver.sh /app/
# cleanup
RUN apt-get remove -y gcc
RUN rm -rf /tmp

WORKDIR /app
USER dcu
ENTRYPOINT ["/app/runserver.sh"]