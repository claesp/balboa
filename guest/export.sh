#!/bin/bash
set -euo pipefail
# Use a built-in serial driver so minimal installations can export evidence.
stty -F /dev/ttyS1 raw -echo 115200
tar -C /var/lib/balboa -czf - evidence > /dev/ttyS1
