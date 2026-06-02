"""
One-time utility: read ~/.sfdx/edgelabs.admin@onedge.co.json and print
the three SF_ env vars required by SalesforceClient.

Usage (local only — never run in production):
    python scripts/bootstrap_sf_creds.py

Paste output into .env and AWS Secrets Manager before deployment.
"""
from __future__ import annotations

import json
import pathlib
import sys

SFDX_FILE = pathlib.Path.home() / ".sfdx" / "edgelabs.admin@onedge.co.json"


def main() -> None:
    if not SFDX_FILE.exists():
        print(f"ERROR: {SFDX_FILE} not found. Run `sf org login web` first.", file=sys.stderr)
        sys.exit(1)
    with SFDX_FILE.open() as f:
        creds = json.load(f)
    print(f"SF_REFRESH_TOKEN={creds['refreshToken']}")
    print(f"SF_CLIENT_ID={creds['clientId']}")
    print(f"SF_INSTANCE_URL={creds['instanceUrl']}")


if __name__ == "__main__":
    main()
