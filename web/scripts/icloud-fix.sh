#!/usr/bin/env bash
# Restaura los symlinks node_modules y .next a sus carpetas .nosync para que iCloud
# Drive no evicte archivos. macOS excluye del sync cualquier directorio terminado en
# .nosync, manteniendo los datos dentro del proyecto pero invisibles para iCloud.
#
# Se ejecuta como postinstall: cada `npm install` recrea node_modules como directorio
# real dentro de iCloud, y este script lo mueve a node_modules.nosync y repone el symlink.
#
# Idempotente y guardado: solo corre si el cwd vive dentro de iCloud Drive.
set -euo pipefail

case "$PWD" in
  *com~apple~CloudDocs*) ;;
  *)
    exit 0
    ;;
esac

fix_dir() {
  local name="$1"
  local target="${name}.nosync"

  if [[ -L "$name" && "$(readlink "$name")" == "$target" ]]; then
    return 0
  fi

  if [[ -d "$name" && ! -L "$name" ]]; then
    echo "[icloud-fix] $name -> $target (excluyendo de iCloud sync)"
    rm -rf "${target}.tmp"
    mv "$name" "${target}.tmp"
    rm -rf "$target"
    mv "${target}.tmp" "$target"
    ln -s "$target" "$name"
  elif [[ ! -e "$name" && -d "$target" ]]; then
    ln -s "$target" "$name"
  fi
}

fix_dir node_modules
fix_dir .next
