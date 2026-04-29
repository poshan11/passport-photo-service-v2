# Stage 1: Build Stage using full Python 3.9 (buster)
FROM python:3.9-bullseye as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CMAKE_BUILD_PARALLEL_LEVEL=1
ENV MAKEFLAGS=-j1

WORKDIR /app

# Install build dependencies including pkg-config and libboost-all-dev
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libboost-all-dev \
    libgl1-mesa-glx \
    libjpeg-dev \
    zlib1g-dev \
    libtiff-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies.
# Note: Do not force --only-binary now so that pip can choose a precompiled wheel.
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Copy the rest of your code.
COPY . /app/

# Stage 2: Final Stage using full Python 3.9 (buster)
FROM python:3.9-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install only runtime libraries needed for your app.
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libtiff-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy the installed packages and code from the builder stage.
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

EXPOSE 5001
#CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "apis:app"]
CMD sh -c 'gunicorn -w 4 -b 0.0.0.0:${PORT:-5001} apis:app'
