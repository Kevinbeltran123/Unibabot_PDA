#!/usr/bin/env node
/*
 * Postinstall portable: solo activa el workaround de iCloud Drive si el
 * proyecto vive bajo `~/Library/Mobile Documents/com~apple~CloudDocs/`.
 * En Windows, Linux, Docker (Alpine, Debian) y macOS sin iCloud hace exit 0.
 *
 * El workaround mueve `node_modules` y `.next` a directorios `.nosync/` y
 * deja symlinks en su lugar. macOS excluye del sync cualquier directorio
 * cuyo nombre termine en `.nosync`. Sin esto, iCloud puede evictar archivos
 * de node_modules en pleno desarrollo.
 *
 * Reemplaza la version anterior en bash, que requeria bash en PATH y
 * fallaba en Windows nativo y en imagenes Alpine sin bash instalado.
 */

const fs = require("fs");
const path = require("path");

function isInICloud() {
  const cwd = process.cwd();
  return cwd.includes("com~apple~CloudDocs");
}

function fixDir(name) {
  const target = `${name}.nosync`;

  // Caso 1: ya es symlink al .nosync, nada que hacer.
  try {
    const stats = fs.lstatSync(name);
    if (stats.isSymbolicLink()) {
      const link = fs.readlinkSync(name);
      if (link === target) return;
    }
  } catch (e) {
    if (e.code !== "ENOENT") throw e;
  }

  // Caso 2: existe como directorio real (lo creo npm install). Mover.
  const exists = fs.existsSync(name);
  const isReal = exists && !fs.lstatSync(name).isSymbolicLink();
  if (isReal) {
    console.log(`[icloud-fix] ${name} -> ${target} (excluyendo de iCloud sync)`);
    const tmp = `${target}.tmp`;
    if (fs.existsSync(tmp)) fs.rmSync(tmp, { recursive: true, force: true });
    fs.renameSync(name, tmp);
    if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true });
    fs.renameSync(tmp, target);
    fs.symlinkSync(target, name, "dir");
    return;
  }

  // Caso 3: no existe y .nosync ya esta listo, repongo el symlink.
  if (!exists && fs.existsSync(target)) {
    fs.symlinkSync(target, name, "dir");
  }
}

function main() {
  if (!isInICloud()) {
    // Windows / Linux / Docker / macOS sin iCloud: no hacer nada.
    return;
  }
  if (process.platform !== "darwin") {
    // En el caso raro de un mount con "com~apple~CloudDocs" fuera de macOS,
    // no aplicamos el workaround porque los symlinks pueden comportarse
    // distinto en Windows / Linux.
    return;
  }
  fixDir("node_modules");
  fixDir(".next");
}

main();
