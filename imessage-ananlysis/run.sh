#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "═══════════════════════════════════════"
echo "  iMessage Metrics"
echo "═══════════════════════════════════════"
echo

echo "📇  Dumping contacts..."
if [ ! -f ./dump_contacts ]; then
    echo "    Compiling dump_contacts.swift..."
    swiftc -o dump_contacts dump_contacts.swift -framework Contacts
fi
./dump_contacts > contacts.json 2>/dev/null && \
    echo "    ✅  contacts.json written" || \
    echo "    ⚠️   Contacts access denied — skipping"
echo

echo "💬  Extracting messages..."
python3 explore.py
echo

echo "📊  Running analysis..."
echo
if [ -d .venv ]; then
    source .venv/bin/activate
fi
python3 me_analysis.py
