#!/bin/bash

nohup sudo socat TCP-LISTEN:30672,fork,reuseaddr TCP:192.168.49.2:30672 > /tmp/socat.log 2>&1 &

echo "Port forwarding started. Check logs with: tail -f /tmp/socat.log"