FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates wget sudo nano \
      python3 python3-venv \
      tigervnc-standalone-server tigervnc-common \
      novnc websockify openbox xterm dbus-x11 \
      supervisor \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash seiscomp \
    && echo "seiscomp ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/seiscomp

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 6080
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
