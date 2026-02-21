#!/bin/bash
# project-index.sh - Generate minified codebase structure index
# Hook type: SessionStart, PostToolUse (on file changes)
# Triggers when: Session begins or files are modified
#
# This hook maintains a lightweight JSON index of the codebase containing:
# - File paths and structure
# - Import/export statements
# - Function and class signatures
# - Key dependencies
#
# The index is stored OUTSIDE Claude's context window, allowing sub-agents
# to reference codebase structure without loading full files.
#
# Based on: "Project Index" concept from Claude Code expert discussions

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INDEX_FILE="$PROJECT_DIR/.claude/project-index.json"
INDEX_DIR="$PROJECT_DIR/.claude"

# Only run for projects with source code
if [ ! -d "$PROJECT_DIR/src" ] && [ ! -d "$PROJECT_DIR/lib" ] && [ ! -d "$PROJECT_DIR/app" ]; then
    # Check for common source patterns
    SRC_COUNT=$(find "$PROJECT_DIR" -maxdepth 2 -name "*.py" -o -name "*.ts" -o -name "*.js" 2>/dev/null | head -5 | wc -l)
    if [ "$SRC_COUNT" -eq 0 ]; then
        exit 0
    fi
fi

# Ensure .claude directory exists
mkdir -p "$INDEX_DIR"

# Generate index
generate_index() {
    local output="{"
    output+='"generated":"'$(date -Iseconds)'",'
    output+='"project":"'$(basename "$PROJECT_DIR")'",'
    output+='"files":['

    local first=true

    # Find source files (Python, TypeScript, JavaScript)
    while IFS= read -r -d '' file; do
        # Skip build artifacts, dependencies, and hidden directories
        if [[ "$file" == *"node_modules"* ]] || \
           [[ "$file" == *"venv"* ]] || \
           [[ "$file" == *".venv"* ]] || \
           [[ "$file" == *"__pycache__"* ]] || \
           [[ "$file" == *".git"* ]] || \
           [[ "$file" == *".claude"* ]] || \
           [[ "$file" == *".next"* ]] || \
           [[ "$file" == *"dist/"* ]] || \
           [[ "$file" == *"build/"* ]] || \
           [[ "$file" == *"coverage/"* ]] || \
           [[ "$file" == *".cache"* ]] || \
           [[ "$file" == *".tox"* ]] || \
           [[ "$file" == *".pytest_cache"* ]] || \
           [[ "$file" == *".mypy_cache"* ]]; then
            continue
        fi

        local relpath="${file#$PROJECT_DIR/}"
        local ext="${file##*.}"

        # Extract signatures based on file type
        local signatures=""
        local imports=""

        case "$ext" in
            py)
                # Python: Extract class/function definitions and imports
                signatures=$(grep -n "^class \|^def \|^async def " "$file" 2>/dev/null | head -20 | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')
                imports=$(grep -n "^import \|^from .* import " "$file" 2>/dev/null | head -10 | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')
                ;;
            ts|tsx|js|jsx)
                # TypeScript/JavaScript: Extract exports, classes, functions
                signatures=$(grep -n "^export \|^class \|^function \|^const .* = \|^interface \|^type " "$file" 2>/dev/null | head -20 | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')
                imports=$(grep -n "^import " "$file" 2>/dev/null | head -10 | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')
                ;;
        esac

        if [ "$first" = true ]; then
            first=false
        else
            output+=","
        fi

        output+='{"path":"'"$relpath"'"'
        if [ -n "$signatures" ]; then
            output+=',"signatures":"'"$signatures"'"'
        fi
        if [ -n "$imports" ]; then
            output+=',"imports":"'"$imports"'"'
        fi
        output+='}'

    done < <(find "$PROJECT_DIR" -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) -print0 2>/dev/null)

    output+='],'

    # Add directory structure summary
    output+='"structure":['
    local struct_first=true
    while IFS= read -r dir; do
        if [[ "$dir" == *"node_modules"* ]] || \
           [[ "$dir" == *"venv"* ]] || \
           [[ "$dir" == *".venv"* ]] || \
           [[ "$dir" == *"__pycache__"* ]] || \
           [[ "$dir" == *".git"* ]] || \
           [[ "$dir" == *".next"* ]] || \
           [[ "$dir" == *"dist"* ]] || \
           [[ "$dir" == *"build"* ]] || \
           [[ "$dir" == *"coverage"* ]] || \
           [[ "$dir" == *".cache"* ]] || \
           [[ "$dir" == *".tox"* ]] || \
           [[ "$dir" == *".pytest_cache"* ]] || \
           [[ "$dir" == *".mypy_cache"* ]]; then
            continue
        fi
        local reldir="${dir#$PROJECT_DIR/}"
        if [ -n "$reldir" ] && [ "$reldir" != "." ]; then
            if [ "$struct_first" = true ]; then
                struct_first=false
            else
                output+=","
            fi
            output+='"'"$reldir"'"'
        fi
    done < <(find "$PROJECT_DIR" -type d -maxdepth 3 2>/dev/null)
    output+=']'

    output+='}'

    echo "$output"
}

# Check if index needs regeneration (older than 5 minutes or doesn't exist)
REGEN=false
if [ ! -f "$INDEX_FILE" ]; then
    REGEN=true
else
    # Check age on Linux/Mac
    if [ "$(uname)" = "Darwin" ]; then
        INDEX_AGE=$(( $(date +%s) - $(stat -f %m "$INDEX_FILE") ))
    else
        INDEX_AGE=$(( $(date +%s) - $(stat -c %Y "$INDEX_FILE") ))
    fi

    if [ "$INDEX_AGE" -gt 300 ]; then
        REGEN=true
    fi
fi

if [ "$REGEN" = true ]; then
    INDEX_CONTENT=$(generate_index)
    echo "$INDEX_CONTENT" > "$INDEX_FILE"
    echo "Project index updated: $INDEX_FILE"
    echo "Use this index to understand codebase structure without loading full files."
fi

exit 0
