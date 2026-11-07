#!/bin/bash
set -euo pipefail
# Use a built-in serial driver so minimal installations can export evidence.
stty -F /dev/ttyS1 raw -echo 115200
printf '\nBALBOA_EVIDENCE_V1\n' > /dev/ttyS1
tar -C /var/lib/balboa -czf - evidence | cat > /dev/ttyS1
python3 - <<'PY'
import os
import termios
fd = os.open("/dev/ttyS1", os.O_WRONLY | os.O_NOCTTY)
termios.tcdrain(fd)
os.close(fd)
PY
