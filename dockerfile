FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y bash gcc git jq wget g++ make && \
    apt-get clean

RUN mkdir -p ~/miniconda3 && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O ~/miniconda3/miniconda.sh && \
    bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3 && \
    rm -rf ~/miniconda3/miniconda.sh && \
    ~/miniconda3/bin/conda init bash

ENV PATH=$PATH:~/miniconda3/bin
WORKDIR /

RUN  ~/miniconda3/bin/pip install --upgrade pip && \
    ~/miniconda3/bin/pip install gitpython

CMD ["/bin/bash"]