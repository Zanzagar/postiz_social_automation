#!/usr/bin/env bash
# check-doc-deps.sh — Check dependencies for Anthropic document processing skills
# Usage: ./scripts/check-doc-deps.sh [--install] [--skill pdf|docx|pptx|xlsx]
#
# Reports which dependencies are available and which are missing.
# With --install, provides copy-pasteable install commands.

set -euo pipefail

# Colors (disabled if not a terminal)
if [ -t 1 ]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    GREEN=''; RED=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

SHOW_INSTALL=false
FILTER_SKILL=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --install) SHOW_INSTALL=true; shift ;;
        --skill) FILTER_SKILL="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--install] [--skill pdf|docx|pptx|xlsx]"
            echo "  --install    Show install commands for missing dependencies"
            echo "  --skill X    Check only dependencies for a specific skill"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Track results
TOTAL=0; FOUND=0; MISSING=0

check_cmd() {
    local name="$1" required_by="$2"
    TOTAL=$((TOTAL + 1))
    if command -v "$name" &>/dev/null; then
        printf "  ${GREEN}✓${NC} %-20s %s\n" "$name" "(${required_by})"
        FOUND=$((FOUND + 1))
    else
        printf "  ${RED}✗${NC} %-20s %s\n" "$name" "(${required_by})"
        MISSING=$((MISSING + 1))
    fi
}

check_python() {
    local pkg="$1" import_name="${2:-$1}" required_by="$3"
    TOTAL=$((TOTAL + 1))
    if python3 -c "import $import_name" &>/dev/null; then
        printf "  ${GREEN}✓${NC} %-20s %s\n" "$pkg" "(${required_by})"
        FOUND=$((FOUND + 1))
    else
        printf "  ${RED}✗${NC} %-20s %s\n" "$pkg" "(${required_by})"
        MISSING=$((MISSING + 1))
    fi
}

check_node() {
    local pkg="$1" required_by="$2"
    TOTAL=$((TOTAL + 1))
    if npm list -g "$pkg" &>/dev/null 2>&1; then
        printf "  ${GREEN}✓${NC} %-20s %s\n" "$pkg" "(${required_by})"
        FOUND=$((FOUND + 1))
    else
        printf "  ${RED}✗${NC} %-20s %s\n" "$pkg" "(${required_by})"
        MISSING=$((MISSING + 1))
    fi
}

printf "\n${BOLD}Anthropic Document Skills — Dependency Check${NC}\n"
printf "═══════════════════════════════════════════════\n\n"

# --- PDF ---
if [ -z "$FILTER_SKILL" ] || [ "$FILTER_SKILL" = "pdf" ]; then
    printf "${BLUE}PDF Skill${NC} — Read, extract tables, fill forms, merge/split\n"
    check_python "pypdf" "pypdf" "pdf"
    check_python "pdfplumber" "pdfplumber" "pdf: table extraction"
    check_python "reportlab" "reportlab" "pdf: creation"
    check_python "pypdfium2" "pypdfium2" "pdf: rendering"
    check_cmd "pdftotext" "pdf: text extraction"
    check_cmd "qpdf" "pdf: merge/split/encrypt"
    check_cmd "pdftk" "pdf: form filling alt"
    check_cmd "tesseract" "pdf: OCR (optional)"
    printf "\n"
fi

# --- DOCX ---
if [ -z "$FILTER_SKILL" ] || [ "$FILTER_SKILL" = "docx" ]; then
    printf "${BLUE}DOCX Skill${NC} — Create & edit Word docs, tracked changes, comments\n"
    check_node "docx" "docx: document creation (JS)"
    check_python "defusedxml" "defusedxml" "docx: XML parsing"
    check_cmd "soffice" "docx: accept tracked changes"
    printf "\n"
fi

# --- PPTX ---
if [ -z "$FILTER_SKILL" ] || [ "$FILTER_SKILL" = "pptx" ]; then
    printf "${BLUE}PPTX Skill${NC} — Slide decks, layouts, charts, speaker notes\n"
    check_node "pptxgenjs" "pptx: slide creation (JS)"
    check_cmd "soffice" "pptx: PDF export, thumbnails"
    check_cmd "pdftoppm" "pptx: slide thumbnails"
    printf "\n"
fi

# --- XLSX ---
if [ -z "$FILTER_SKILL" ] || [ "$FILTER_SKILL" = "xlsx" ]; then
    printf "${BLUE}XLSX Skill${NC} — Formulas, analysis, charts\n"
    check_python "openpyxl" "openpyxl" "xlsx: read/write"
    check_python "pandas" "pandas" "xlsx: data analysis"
    check_cmd "soffice" "xlsx: formula recalculation"
    printf "\n"
fi

# --- Summary ---
printf "═══════════════════════════════════════════════\n"
if [ "$MISSING" -eq 0 ]; then
    printf "${GREEN}${BOLD}All $TOTAL dependencies found.${NC} Document skills ready.\n"
else
    printf "${YELLOW}${BOLD}$FOUND/$TOTAL found, $MISSING missing.${NC}\n"
fi

# --- Install commands ---
if [ "$SHOW_INSTALL" = true ] && [ "$MISSING" -gt 0 ]; then
    printf "\n${BOLD}Install commands (Ubuntu/Debian):${NC}\n"
    printf "─────────────────────────────────\n"

    # System packages
    APTPKGS=""
    command -v soffice &>/dev/null || APTPKGS="$APTPKGS libreoffice-calc libreoffice-writer libreoffice-impress"
    command -v pdftotext &>/dev/null || APTPKGS="$APTPKGS poppler-utils"
    command -v pdftoppm &>/dev/null || APTPKGS="$APTPKGS poppler-utils"
    command -v qpdf &>/dev/null || APTPKGS="$APTPKGS qpdf"
    command -v pdftk &>/dev/null || APTPKGS="$APTPKGS pdftk-java"
    command -v tesseract &>/dev/null || APTPKGS="$APTPKGS tesseract-ocr"

    if [ -n "$APTPKGS" ]; then
        # Deduplicate
        APTPKGS=$(echo "$APTPKGS" | tr ' ' '\n' | sort -u | tr '\n' ' ')
        printf "\n  ${BOLD}sudo apt install -y${NC} $APTPKGS\n"
    fi

    # Python packages
    PIPPKGS=""
    python3 -c "import pypdf" &>/dev/null || PIPPKGS="$PIPPKGS pypdf"
    python3 -c "import pdfplumber" &>/dev/null || PIPPKGS="$PIPPKGS pdfplumber"
    python3 -c "import reportlab" &>/dev/null || PIPPKGS="$PIPPKGS reportlab"
    python3 -c "import pypdfium2" &>/dev/null || PIPPKGS="$PIPPKGS pypdfium2"
    python3 -c "import openpyxl" &>/dev/null || PIPPKGS="$PIPPKGS openpyxl"
    python3 -c "import pandas" &>/dev/null || PIPPKGS="$PIPPKGS pandas"
    python3 -c "import defusedxml" &>/dev/null || PIPPKGS="$PIPPKGS defusedxml"

    if [ -n "$PIPPKGS" ]; then
        printf "\n  ${BOLD}pip install${NC}$PIPPKGS\n"
    fi

    # Node packages
    NPMPKGS=""
    npm list -g docx &>/dev/null 2>&1 || NPMPKGS="$NPMPKGS docx"
    npm list -g pptxgenjs &>/dev/null 2>&1 || NPMPKGS="$NPMPKGS pptxgenjs"

    if [ -n "$NPMPKGS" ]; then
        printf "\n  ${BOLD}npm install -g${NC}$NPMPKGS\n"
    fi

    # NODE_PATH note (always show if npm packages are needed by skills)
    if npm list -g docx &>/dev/null 2>&1 || npm list -g pptxgenjs &>/dev/null 2>&1; then
        printf "\n  ${YELLOW}Note:${NC} Global npm packages need NODE_PATH for scripts:\n"
        printf "  export NODE_PATH=\$(npm root -g)\n"
    fi

    printf "\n${BOLD}Install commands (macOS):${NC}\n"
    printf "─────────────────────────────────\n"

    BREWPKGS=""
    command -v soffice &>/dev/null || BREWPKGS="$BREWPKGS --cask libreoffice"
    command -v pdftotext &>/dev/null || BREWPKGS="$BREWPKGS poppler"
    command -v qpdf &>/dev/null || BREWPKGS="$BREWPKGS qpdf"
    command -v tesseract &>/dev/null || BREWPKGS="$BREWPKGS tesseract"

    if [ -n "$BREWPKGS" ]; then
        printf "\n  ${BOLD}brew install${NC}$BREWPKGS\n"
    fi

    if [ -n "$PIPPKGS" ]; then
        printf "\n  ${BOLD}pip install${NC}$PIPPKGS\n"
    fi
    if [ -n "$NPMPKGS" ]; then
        printf "\n  ${BOLD}npm install -g${NC}$NPMPKGS\n"
    fi
fi

printf "\n"
