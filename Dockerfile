FROM python:3.8

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apt-get update && apt-get install -y cmake nasm meson ninja-build
RUN git clone https://git.ffmpeg.org/ffmpeg.git
RUN pip install --no-cache-dir -r requirements.txt
RUN git clone https://github.com/Netflix/vmaf.git && cd vmaf && make install
RUN cd vmaf/python && python setup.py install && cd ../..
RUN cd ffmpeg && ./configure --enable-libvmaf && make install -j
RUN ldconfig

#TODO build HM and VTM for conformance checking

COPY examples/docker_cfg.py my_cfg.py

COPY . .

ENTRYPOINT ["python"]
