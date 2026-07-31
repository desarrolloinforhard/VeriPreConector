# Changelog

## 1.16.25 - 2026-07-31

- Added an in-app Android image specification guide for product images and company logos under `Configuracion de Datos`.
- Logo selection now auto-normalizes to a 4:1 PNG with safe inner margins before saving to assets.
- Manual product image uploads now optimize to Android-friendly JPEG dimensions and weight before storing in SQLite.
- Automatic image ingestion via `image_resolver.py` now applies the same normalization for local folders, custom API, and GO-UPC sources.

## 1.16.24 - 2026-07-30

- Added automatic promotion for Windows local administrators so newly detected admin users no longer remain blocked as pending.
- Exposed Windows admin role in the `Usuarios y Permisos` screen for the current user and detected local users.
- Continued hardening of the SmartPrice build flow and versioned release packaging.

## 1.16.23 - 2026-07-30

- Baseline version currently used by SmartPrice in `versionado/version.txt`.
- Includes the recent work around device discovery, shared config handling, single-instance hardening, and release-state documentation.
- Adds a CobrosHub-style build/release pipeline based on `VERSION_MANIFEST.json`, PyInstaller config, and packaging scripts.
