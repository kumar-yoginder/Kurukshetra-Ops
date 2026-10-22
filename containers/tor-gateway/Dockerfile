FROM debian:trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad
RUN apt-get update && apt-get install -y --no-install-recommends tor wireguard-tools iproute2 nftables python3 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY torrc /etc/tor/torrc
COPY firewall.nft.in /usr/local/share/tor-gateway/firewall.nft.in
COPY entrypoint.sh healthcheck.py /usr/local/bin/
RUN chmod 0755 /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.py
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
