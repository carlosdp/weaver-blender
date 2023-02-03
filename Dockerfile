FROM rrdockerhub/cudagl:11.7.1-base-runtime-ubuntu20.04

RUN rm -rf /var/lib/apt/lists/*
RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  wget curl unzip git xz-utils libxrender-dev libxxf86vm-dev libxfixes-dev libxi-dev libxkbcommon-dev \
  libglvnd0 libgl1 libglx0 libegl1 libxext6 libx11-6 libsndfile-dev libavdevice-dev ffmpeg ocl-icd-libopencl1 python3 python3-pip python3-dev ca-certificates

RUN ln -s libOpenCL.so.1 /usr/lib/x86_64-linux-gnu/libOpenCL.so

# Download and install Blender

RUN wget https://mirrors.ocf.berkeley.edu/blender/release/Blender3.4/blender-3.4.1-linux-x64.tar.xz \
  && tar -xvf blender-3.4.1-linux-x64.tar.xz --strip-components=1 -C /bin \
  && rm -rf blender-3.4.1-linux-x64.tar.xz \
  && rm -rf blender-3.4.1-linux-x64

ENV BLENDER_PATH "/bin/3.4"
ENV BLENDERPIP "/bin/3.4/python/bin/pip3"
ENV BLENDERPY "/bin/3.4/python/bin/python3.10"
ENV HW="GPU"

# Download the Python source since it is not bundled with Blender

RUN wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz \
  && tar -xzf Python-3.10.0.tgz \
  && cp -r Python-3.10.0/Include/* $BLENDER_PATH/python/include/python3.10/ \
  && rm -rf Python-3.10.0.tgz \
  && rm -rf Python-3.10.0

WORKDIR /workspace

# RUN ${BLENDERPY} -m ensurepip && ${BLENDERPIP} install --upgrade pip && ${BLENDERPIP} install -r requirements.txt

RUN mkdir /workspace/weaver_blender
COPY ./setup.py /workspace/

RUN pip install .

ENV SSL_CERT_FILE /etc/ssl/certs/ca-certificates.crt

COPY . /workspace

CMD ["python3", "-u", "handler.py"]