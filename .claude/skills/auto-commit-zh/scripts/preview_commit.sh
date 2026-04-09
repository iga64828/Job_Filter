#!/usr/bin/env bash
set -euo pipefail

echo "[git status --short]"
git status --short
echo

echo "[staged files]"
git diff --cached --name-only
echo

echo "[unstaged files]"
git diff --name-only
