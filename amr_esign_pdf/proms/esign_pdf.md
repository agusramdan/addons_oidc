Buat modul Odoo 13 bernama `amr_esign_pdf` di `../` untuk mendukung PDF Multiple Signature (PAdES).

Spesifikasi:

Model `pdf.document`:
- `name` (Char)
- `pdf_file` (Binary, filename `pdf_filename`)
- `pdf_hash` (Char) → hash dari PDF untuk request CMS
- `pdf_lock` (Binary) → PDF dengan placeholder ruang signature
- `signed_pdf` (Binary, filename `signed_pdf_filename`)
- `state` (Selection: draft, request, signed)

Model `pdf.sign`:
- `name` (Char)
- `pdf_document_id` (Many2one ke `pdf.document`)
- `partner_id` (Many2one ke `res.partner`)
- `signature_index` (Integer) atau `signature_name`
- `cms_data` (Binary, CMS hasil CA)
- `state` (Selection: draft, requested, signed)

Fitur:
- Upload PDF pada `pdf.document`
- Generate / simpan `pdf_lock` dengan ruang CMS untuk signature berikutnya
- Hitung hash PDF dan tampilkan `pdf_hash`
- Request CMS ke CA menggunakan `pdf_hash`
- Simpan `cms_data` di `pdf.sign`
- Tambahkan tombol untuk:
  - `Prepare Signature` / `Request CMS`
  - `Apply CMS`
  - `Reset`
- Tambahkan tombol `Sign pdf` Untuk Generate `signed_pdf` setelah semua `pdf.sign` mempunyai signed.

Views & menu:
- Form view + tree view untuk `pdf.document`
- Form view + tree view untuk `pdf.sign`
- Menu item dan action `ir.actions.act_window`

Security:
- Tambahkan `security/ir.model.access.csv` untuk akses user

Manifest:
- Buat `__manifest__.py` dengan urutan: `name`, `version`, `category`, `summary`, `description`, `author`, `website`, `license`, `depends`, `data`, `demo`, `assets`, `installable`, `auto_install`, `application`, `externaldepenency`


Implementasi logika PAdES nyata menggunakan pyHanko (mencakup: prepare lock, calculate ByteRange, generate hash, apply CMS, incremental updates).

Catatan: gunakan ORM Odoo, hindari raw SQL, dan jangan letakkan business logic di controller. Ikuti standar Odoo 13 / OCA.

buatkan tests case untuk addons ini.
