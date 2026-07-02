Buat modul Odoo 13 bernama `amr_esign_pdf`
Odoo 13 untuk PDF Multiple Signature (PAdES).

dependency
- pyHanko 0.20.1

Spesifikasi:

Model `user.ca.data`:
- `name` (Char)
- `user_id` (Many2one ke `res.users`)
- `certificate` (Text) PEM 
- `private_key` (Text) PEM
- `public_key` (Text) PEM

Model `pdf.document`:
- `name` (Char)
- `pdf_file` (Binary, filename `pdf_filename`)
- `signed_pdf` (Binary, filename `signed_pdf_filename`)
- `state` (Selection: draft, signed) 
- `signature_ids` (One2many ke `pdf.sign`, 'pdf_document_id', string='Signatures')

Model `pdf.sign`:
- `pdf_document_id` (Many2one ke `pdf.document`)
- `user_ca_data_id` (Many2one ke `user.ca.data`) 
- `seq` (Integer) squence untuk urutan signature
- `name` (Char) as sig_field_name
- `on_page` (Integer) untuk menentukan halaman signature
- `box` (Char) untuk menentukan posisi signature "x0, y0, x1, y1"
- `deep_link` (Char) untuk signature QR code

Views & menu:
- Form view + tree view untuk `pdf.document`
- Form view + tree view untuk `pdf.sign`
- Form view + tree view untuk `user.ca.data`
- Menu item dan action `ir.actions.act_window` pisahkan menu pada file menuitem.xml

Security:
- Tambahkan `security/ir.model.access.csv` untuk akses user

Manifest:
- Buat `__manifest__.py` dengan urutan: `name`, `version`, `category`, `summary`, `description`, `author`, `website`, `license`, `depends`, `data`, `demo`, `assets`, `installable`, `auto_install`, `application`, `externaldepenency`


Buat method action_sign_pdf Untuk Generate `signed_pdf`.
