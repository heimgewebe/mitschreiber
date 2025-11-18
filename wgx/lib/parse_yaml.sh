#!/usr/bin/env bash
set -euo pipefail

# parse_yaml.sh – sehr einfacher YAML-Parser für flache Key-Value-Paare.
# Quelle: leicht angepasste Variante eines bekannten Snippets
# (siehe ursprüngliche Diskussion auf StackOverflow).
#
# Einschränkungen (bewusst):
# - keine verschachtelten Objekte außer 1 Ebene
# - keine Multi-Line-Strings / Block-Skalare
# - keine Arrays mit '-' Syntax
#
# Für das wgx-Profil reicht das: wir wollen tasks.<name> → "cmd".

parse_yaml() {
  local file="$1"
  local prefix="$2"

  if [[ ! -f "$file" ]]; then
    echo "[wgx] parse_yaml: Datei nicht gefunden: $file" >&2
    return 1
  fi

  local s='[[:space:]]*'
  local w='[a-zA-Z0-9_]*'
  local fs
  fs=$(echo @ | tr @ '\034')

  sed -ne "s|^\($s\)\($w\)$s:$s\"\(.*\)\"$s\$|\1$fs\2$fs\3|p" \
      -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p" "$file" |
    awk -F"$fs" '
      {
        indent = length($1)/2
        vname[indent] = $2
        for (i in vname) if (i > indent) delete vname[i]
        if (length($3) > 0) {
          vn=""; for (i=0; i<indent; i++) vn = vn vname[i] "_"
          printf("%s%s%s=\"%s\"\n", "'"$prefix"'", vn, $2, $3)
        }
      }'
}
