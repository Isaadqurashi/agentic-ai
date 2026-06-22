#!/usr/bin/env bash
set -euo pipefail

export DRY_RUN=true
unset OPENAI_API_KEY
python -m pytest
