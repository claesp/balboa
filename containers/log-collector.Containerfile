ARG BASE
FROM ${BASE}
RUN dnf -y --setopt=install_weak_deps=False install systemd-journal-remote haproxy \
    && systemd-machine-id-setup && dnf clean all
COPY containers/log-collector.cfg /etc/haproxy/balboa.cfg
ENTRYPOINT ["/bin/bash", "-ec", "/usr/lib/systemd/systemd-journal-remote --listen-http=127.0.0.1:19533 --output=/logs/ & exec haproxy -db -f /etc/haproxy/balboa.cfg"]
