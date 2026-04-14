#!/usr/bin/env bash
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

# Config tamper guard — prevent Claude from weakening linter/formatter settings
# Override with: TEMPLATE_ALLOW_CONFIG_EDIT=1
if [[ "${TEMPLATE_ALLOW_CONFIG_EDIT:-0}" != "1" ]]; then
    LINTER_CONFIGS_BLOCK=(
        ".ruff.toml" "ruff.toml"
        ".eslintrc" ".eslintrc.js" ".eslintrc.json" ".eslintrc.yaml"
        "eslint.config.js" "eslint.config.mjs"
        ".prettierrc" ".prettierrc.json"
        "prettier.config.js" "prettier.config.mjs"
        "biome.json" "biome.jsonc"
        ".flake8" ".golangci.yml" ".golangci.yaml"
    )

    for pattern in "${LINTER_CONFIGS_BLOCK[@]}"; do
        if [[ "$FILENAME" == "$pattern" ]]; then
            echo "BLOCKED: Cannot modify linter/formatter config: $FILENAME" >&2
            echo "This protects code quality standards from being weakened." >&2
            echo "To override: export TEMPLATE_ALLOW_CONFIG_EDIT=1" >&2
            exit 2
        fi
    done

    # Warn-only for multi-purpose configs (contain more than just lint rules)
    LINTER_CONFIGS_WARN=("tsconfig.json" "pyproject.toml")
    for pattern in "${LINTER_CONFIGS_WARN[@]}"; do
        if [[ "$FILENAME" == "$pattern" ]]; then
            echo "WARNING: Modifying $FILENAME — ensure lint/format rules are not weakened" >&2
        fi
    done
fi

# Check protected directories
for dir in "${PROTECTED_DIRS[@]}"; do
    if [[ "$FILE_PATH" == *"/$dir/"* ]] || [[ "$DIRNAME" == *"$dir" ]]; then
        echo "BLOCKED: Cannot edit files in protected directory: $dir"
        exit 2
    fi
done

# Allow the edit
exit 0
