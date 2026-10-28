#!/usr/bin/env python3
"""
Dump unpacked RAM by reading JSON data files.
Usage: First save MCP output to JSON, then run this script.
"""
import json
import sys

# This script expects JSON files with MCP debug_read_memory_range output
# Format: {"address": "0x...", "length": N, "data": [...]}

def load_chunk(filepath):
    with open(filepath) as f:
        obj = json.load(f)
    return bytes(obj["data"])

if __name__ == "__main__":
    # For now, just report the issue
    print("Manual dump required: MCP data too large for inline Python arrays.")
    print("Recommendation: Use smaller chunk sizes or direct binary export.")
