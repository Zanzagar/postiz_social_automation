#!/bin/bash
# protect-sensitive-files.sh - Block edits to sensitive files
# Hook type: PreToolUse (matcher: "Edit|Write")
# Triggers when: Claude attempts to edit or write files
#
# Exit codes:
#   0 = Allow the edit
#   2 = Block the edit (protects sensitive files)

# Read the input JSON from stdin
INPUT=$(cat)

# Extract the file path
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')

[ -z "$FILE_PATH" ] && exit 0

# Get just the filename for pattern matching
FILENAME=$(basename "$FILE_PATH")
DIRNAME=$(dirname "$FILE_PATH")

# Protected file patterns
PROTECTED_FILES=(
    ".env"
    ".env.local"
    ".env.production"
    "credentials.json"
    "secrets.json"
    "*.pem"
    "*.key"
    "id_rsa"
    "id_ed25519"
)

# Protected directories
PROTECTED_DIRS=(
    ".git"
    "node_modules"
    "__pycache__"
    ".venv"
    "venv"
)

# Check protected files
for pattern in "${PROTECTED_FILES[@]}"; do
    if [[ "$FILENAME" == $pattern ]]; then
        echo "BLOCKED: Cannot edit protected file: $FILENAME"
        echo "This file may contain sensitive data. Edit manually if needed."
        exit 2
    fi
done

# Check protected directories
for dir in "${PROTECTED_DIRS[@]}"; do
    if [[ "$FILE_PATH" == *"/$dir/"* ]] || [[ "$DIRNAME" == *"$dir" ]]; then
        echo "BLOCKED: Cannot edit files in protected directory: $dir"
        exit 2
    fi
done

# Allow the edit
exit 0
