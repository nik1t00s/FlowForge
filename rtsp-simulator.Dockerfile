FROM alpine:latest

# Install ffmpeg
RUN apk add --no-cache ffmpeg wget tar

# Download and install MediaMTX
RUN wget https://github.com/bluenviron/mediamtx/releases/download/v1.4.1/mediamtx_v1.4.1_linux_amd64.tar.gz \
    && tar -xzf mediamtx_v1.4.1_linux_amd64.tar.gz \
    && mv mediamtx /usr/local/bin/ \
    && rm mediamtx_v1.4.1_linux_amd64.tar.gz

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/mediamtx"]
