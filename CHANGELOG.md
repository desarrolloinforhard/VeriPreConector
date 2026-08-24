# Changelog

## 1.16.35 - 2026-08-24

- Added an informative Home dashboard with local product and advertising metrics, connection state, registered devices, guided shortcuts, and a status bar.
- Added a dedicated Home navigation entry plus theme-aware Inforhard branding assets.
- Refined the corporate light and dark themes with layered green surfaces, consistent contrast, and reduced navigation flashes.
- Improved the Products header, cards, action hierarchy, selected-row contrast, and dark-mode rendering.
- Reorganized Advertising actions into a more compact and consistent layout across both themes.
- Added human-readable catalog dates, actionable empty states, and structured device rows.

## 1.16.34 - 2026-08-21

- Fixed back navigation so returning from Advertising to Products preserves a valid history instead of raising `IndexError`.
- Added defensive recovery for empty or incomplete navigation histories.
- Reduced routine Sybase disconnect logging from `INFO` to `DEBUG` to avoid repetitive operational noise.
- Added regression coverage for Advertising-to-Products, Products-to-Home, single-entry, and empty navigation histories.
- Added a responsive collapsible ttkbootstrap sidebar with stable compact and expanded rendering.
- Kept footer actions at fixed positions, cached sidebar assets, and made Windows layout transitions atomic to prevent flicker.
- Fixed the missing typography token that prevented the About screen from opening.
- Added a persistent light/dark theme selector to the sidebar with compact icon-only rendering.
- Added explicit corporate light and dark palettes for the shell and sidebar controls.
- Improved Product table contrast with dark striped rows and a strong green selection state.
- Made the loading overlay theme-aware to prevent white flashes during dark-mode navigation and reloads.

## 1.16.33 - 2026-08-20

- Changed the tray lifecycle so the SmartPrice icon is created only when the window is sent to the system tray and is explicitly destroyed when the app is restored or closed, reducing duplicate ghost icons in Windows notification overflow.
- Fixed `Transmitir Novedades` so pending product changes are now recovered from local SQLite using persisted `dFechaU` marks instead of relying only on the in-memory `productos_modificados` set for the current session.
- Added persistence of the last successful novedades transmission mark in configuration, allowing next-day transmissions to keep sending pending price changes without forcing a full catalog resend.
- Hardened `Recargar Productos` so the local product list resets Tableview state and filters before repopulating, preventing empty visual lists after a refresh with valid local rows.

## 1.16.32 - 2026-08-19

- Hardened local SQLite access for shared installations using `F:\Dba\veripre.db`, targeting the `database is locked` failures observed in client `Novo`.
- Added internal process locking around the SQLite wrapper so background sync polling, UI reads, and local writes no longer reuse the same connection concurrently.
- Enabled SQLite `busy_timeout`, WAL mode, and safer connection pragmas to reduce transient lock contention on the shared local catalog.
- Removed unnecessary `commit()` calls after read-only queries, preventing avoidable write-lock escalation during automatic synchronization checks.

## 1.16.31 - 2026-08-14

- Hardened the legacy SQL Anywhere/ODBC lifecycle to reduce interference with other client executables sharing the same DBA.
- Switched `ConexionSybase` to short-lived cursor usage with connection health checks and defensive reconnection.
- Enabled `autocommit` in the ODBC wrapper and removed the persistent cursor reference to avoid leaving long-lived read state behind.
- Added explicit Sybase disconnect on SmartPrice shutdown and before replacing the global ODBC connection from configuration screens.
- Documented the DBA/ODBC operational incident and the mitigation baseline pending on-site validation in client `Novo`.

## 1.16.30 - 2026-08-06

- Extended automatic synchronization so the background watcher now detects changes in products, secondary barcodes, packs, price offers, and OFPLU data instead of only `ARTICULO`.
- Added block-level diagnostics for automatic sync, reporting whether the change came from products, codes, packs, price offers, or OFPLU structures.
- Split product offer handling in SmartPrice into `Oferta precio` and `Oferta OFPLU`, allowing both to coexist without visual or payload collisions.
- Updated the product detail modal to mirror the new offer separation, add scoped scrolling for the offer panel, and widen the layout for better readability.

## 1.16.29 - 2026-08-04

- Hardened product DELETE fallback so SmartPrice first tries `/api/veri/batch_productos` and then `/api/veri/ALL_PRODUCTOS` without dropping the `/api` prefix.
- Added explicit DELETE diagnostics in console and device status UI, including the exact endpoint that succeeded or the HTTP/error detail that failed.
- Added payload-side protection to omit invalid `img_base64` values before sending to Android, preventing timestamps or other non-image values from being transmitted as product images.

## 1.16.28 - 2026-08-04

- Added explicit Android configuration delivery for `IMAGES_API_URL` using the same SmartPrice value stored in configuration.
- Product and logo configuration sends now push both `GO_UPC_KEY` and `IMAGES_API_URL` before the main payload.
- Added a manual action in `Configuración > Conexión GO-UPC` to send `GO_UPC_KEY` plus the configured image API URL to the selected device.
- Device status inspection now also reports the current `IMAGES_API_URL` exposed by the Android endpoint.

## 1.16.27 - 2026-08-03

- Removed the operational barcode normalization flow and restored SmartPrice to work with a single `codigo` end to end.
- Product synchronization, local SQLite persistence, product UI, and Android payloads now use the original product code without deriving EAN-13 variants.
- Preserved `PACKS_MINI`, additional prices, and offer synchronization while simplifying the product pipeline.
- Added an automatic SQLite migration for legacy installations so the `productos` table drops `CODIGO_ORIGINAL` and `CODIGO_NORMALIZADO` on next schema verification.
- Hardened file log rotation with a safe rotating handler to avoid `WinError 32` tracebacks when another process holds `veripre.log`.

## 1.16.26 - 2026-07-31

- Added legacy barcode normalization support for clients that store `CCODEBAR` with 12 numeric digits and no check digit.
- SQLite now persists `CODIGO_ORIGINAL` and `CODIGO_NORMALIZADO` for product traceability.
- Product sync now calculates EAN-13 check digits during synchronization without altering the Sybase source value.
- Product payloads sent to Android now prioritize the normalized barcode while preserving the original value locally.
- Validated the migration and a full real synchronization against the installed SmartPrice database in `C:\ProgramData\SmartPrice\veripre.db`.

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
