FROM python:3

RUN apt-get update && \
    apt-get install -y bash gcc git jq wget g++ make && \
    apt-get clean

WORKDIR /

RUN  pip install --upgrade pip && \
    pip install gitpython flask

EXPOSE 5001

CMD ["/bin/bash"]