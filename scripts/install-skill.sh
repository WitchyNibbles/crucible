#!/usr/bin/env bash
# Install cto-dev-team as a Hermes skill via symlink.
# Run from anywhere: bash ~/projects/crucible/scripts/install-skill.sh
set -euo pipefail

REPO_SKILL="$(cd "$(dirname "$0")/.." && pwd)/skills/software-development/cto-dev-team"
HERMES_SKILL="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}/software-development/cto-dev-team"

mkdir -p "$(dirname "$HERMES_SKILL")"

if [ -L "$HERMES_SKILL" ] || [ -e "$HERMES_SKILL" ]; then
    echo "Removing existing skill at $HERMES_SKILL"
    rm -rf "$HERMES_SKILL"
fi

ln -s "$REPO_SKILL" "$HERMES_SKILL"
echo "Installed: $HERMES_SKILL -> $REPO_SKILL"
