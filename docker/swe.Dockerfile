FROM ubuntu:jammy

ARG TARGETARCH

RUN apt-get update && \
    apt-get install -y bash gcc git jq wget g++ make && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /

ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
COPY docker/getconda.sh .
RUN bash getconda.sh ${TARGETARCH} \
    && rm getconda.sh \
    && mkdir /root/.conda \
    && bash miniconda.sh -b \
    && rm -f miniconda.sh
RUN conda --version \
    && conda init bash \
    && conda config --append channels conda-forge

RUN conda create -y -n python3.9 python=3.9
RUN conda create -y -n python3.10 python=3.10

RUN  pip install --upgrade pip && \
    pip install gitpython flask directory_tree pytest

EXPOSE 5001

WORKDIR /

CMD ["/bin/bash"]