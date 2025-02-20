FROM python:3.12-slim AS builder
 
# Set the working directory
WORKDIR /app

# Install deps
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    wget && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Interesting boost is not needed in the runtime
RUN wget https://archives.boost.io/release/1.87.0/source/boost_1_87_0.tar.gz && \
    tar -xzf boost_1_87_0.tar.gz && \
    cd boost_1_87_0 && \
    ./bootstrap.sh --with-libraries=python && \
    ./b2 install --prefix=/usr/local/

# Can refer here to build other platforms https://github.com/Exiv2/exiv2/releases/tag/v0.28.4
RUN wget -O exiv2.tar.gz https://github.com/Exiv2/exiv2/releases/download/v0.28.4/exiv2-0.28.4-Linux-x86_64.tar.gz && \
    mkdir exiv2 && \
    tar -xzf exiv2.tar.gz -C exiv2 --strip-components=1 && \
    cd exiv2 && \
    cp -r include/* /usr/local/include && \
    cp -r lib/* /usr/local/lib && \
    cp -r bin/* /usr/local/bin

# Copy the requirements file
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy only runtime dependencies
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /opt/venv /opt/venv

RUN ldconfig

# Make sure to use the virtual environment
ENV PATH="/opt/venv/bin:$PATH"
ENV LD_LIBRARY_PATH="/usr/local/lib"

# Copy the source code
COPY ./MotionPhotoMuxer.py ./main.py

ENTRYPOINT ["python", "main.py"]