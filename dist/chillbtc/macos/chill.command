#!/usr/bin/env bash
# Launcher macOS — double-cliquable depuis le Finder.
# Installe uv au premier lancement si nécessaire, puis lance ChillBTC.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_DIR="$(cd "$SCRIPT_DIR/../code" && pwd)"

echo ""
echo "  ╔════════════════════════════════════════════════════════╗"
echo "  ║  ChillBTC — BTC posé. Un coup d'œil par mois.          ║"
echo "  ╚════════════════════════════════════════════════════════╝"
echo ""

# S'assure que ~/.local/bin est dans le PATH (install par défaut d'uv)
if [ -d "$HOME/.local/bin" ] && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# 1. Installe uv si absent
if ! command -v uv >/dev/null 2>&1; then
    echo "  → Premier lancement détecté."
    echo "  → Installation de uv (gestionnaire Python, ~5 Mo)…"
    echo ""
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        echo ""
        echo "  ⚠  Installation de uv échouée."
        echo "     Installe manuellement depuis https://docs.astral.sh/uv/"
        echo "     puis relance ce script."
        read -n 1 -s -r -p "  Appuie sur une touche pour fermer…"
        exit 1
    fi
    echo ""
    echo "  ✓ uv installé."
    echo ""
fi

# 2. uv sync (1ʳᵉ fois : télécharge Python + deps, 30 s - 2 min selon connexion)
if [ ! -d "$CODE_DIR/.venv" ]; then
    echo "  → Installation de Python et des dépendances…"
    echo "    (pandas, numpy, matplotlib, requests — ~80 Mo à télécharger)"
    echo "    Cette étape ne se fait qu'une seule fois."
    echo ""
fi

cd "$CODE_DIR"
exec uv run chillbtc "$@"
