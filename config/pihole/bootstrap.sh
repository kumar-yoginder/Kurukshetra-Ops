#!/bin/sh
set -eu
# Seed fresh deployments; existing databases retain their UI-managed lists.
if [ ! -f /etc/pihole/gravity.db ]; then
    cp /bootstrap/adlists.list /etc/pihole/adlists.list
fi
# Adjust only the built-in Gravity job; retain Pi-hole's other scheduled tasks.
awk '/pihole updateGravity/ {$1=47; $2=3; $3="*"; $4="*"; $5="*"} {print}' /crontab.txt > /tmp/pihole-crontab
mv /tmp/pihole-crontab /crontab.txt
exec /usr/bin/start.sh "$@"
