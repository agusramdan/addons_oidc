# Spesifikasi Modul amr_esign_pdf

Modul Odoo 13 untuk workflow tanda tangan PDF multiple signature (PAdES) yang saat ini telah diimplementasikan dengan model, view, wizard, dan menu pada folder [addons_token/amr_esign_pdf](addons_token/amr_esign_pdf).

## Definisi
- PEM adalah format teks yang berisi data sertifikat atau kunci dalam format Base64 dengan header dan footer standar.
- Cloud Signature Consortium API Specifications untuk melakukan inegrasi provaider remote CSC API v2.2 Specification

## Dependency
lihat [amr_esign_pdf](amr_esign_pdf/requirements.txt)
Gunakan infomasi requierments.txt untuk menentukan generate python terutma untuk phangko 

## Model yang tersedia saat ini

### Model `pdf.sign.template`
- `name` (Char)
- `active` (Boolean)
- `company_id` (Many2one ke `res.company`)
- `template_type` (Selection: `pdf`, `image`)
- `pdf_template` (Binary)
- `pdf_template_filename` (Char)
- `image_template` (Binary)
- `image_template_filename` (Char)
- `width` (Float)
- `height` (Float)

### Model `user.ca.data`
- `name` (Char)
- `user_id` (Many2one ke `res.users`)
- `certificate` (Text PEM)
- `private_key` (Text PEM)
- `public_key` (Text PEM)

### Model `pdf.document`
- `name` (Char)
- `state` (Selection: `draft`, `request`, `signed`)
- `provider` (Selection: `internal`,`rscd`, `sca`) rscd: Sign Hash , sca: Sign Doc 
- `template_id` (Many2one ke `pdf.sign.template`)
- `pdf_file` (Binary, filename `pdf_filename`)
- `pdf_filename` (Char)
- `pdf_hash` (Char, readonly)
- `pdf_lock_file` (Binary, filename `pdf_lock_filename`)
- `pdf_lock_filename` (Char)
- `pdf_lock_hash` (Char, readonly)
- `signed_pdf` (Binary, filename `signed_pdf_filename`)
- `signed_pdf_filename` (Char, readonly)
- `signature_ids` (One2many ke `pdf.sign`)

### Model `pdf.sign`
- `name` (Char, dipakai sebagai nama field signature)
- `seq` (Integer)
- `pdf_document_id` (Many2one ke `pdf.document`)
- `template_id` (Related ke `pdf.document.template_id`)
- `user_ca_data_id` (Many2one ke `user.ca.data`)
- `placeholder` (Char)
- `placeholder_remove` (Boolean)
- `width` (Float)
- `height` (Float)
- `page_box` (Char)
- `deep_link` (Char)
- `cms_data` (Binary, CMS hasil CA)
- `state` (Selection: draft, requested, signed)
- `prepared_pdf` (Binary, readonly)
- `document_digest` (Binary, readonly) base64 krim ke CSC
- `raw_signature` (Binary, readonly) base64 dari CSC 

## Wizard `user.ca.data.wizard`
- `name`
- `user_id`
- `org_name`
- `algorithm`
- `validity_days`
- `serial_number`
- `certificate`
- `private_key`

## View dan menu
- Form dan tree view untuk `pdf.document`
- Form dan tree view untuk `pdf.sign`
- Form dan tree view untuk `user.ca.data`
- Form view, action, dan menu untuk `user.ca.data.wizard`
- Menu item dipisahkan di file [amr_esign_pdf/views/menuitems.xml](amr_esign_pdf/views/menuitems.xml)

## Fitur yang sudah ada
- `action_prepare_signature`
- `action_reset`
- `action_sign_pdf`

## Penjelasan alur tanda tangan
- `placeholder` dipakai untuk mencari posisi tanda tangan di halaman PDF.
- `page_box` dipakai untuk posisi manual dengan format `page/x0,y0,x1,y1`.
- `name` dipakai sebagai nama field signature yang akan dibuat pada PDF.

## Catatan penyesuaian
Dokumen ini disusun sesuai kondisi modul yang ada saat ini. Beberapa field pada spesifikasi awal belum ada di model aktif, sehingga penamaan dan struktur field berikut disesuaikan dengan implementasi yang benar-benar tersedia di [addons_token/amr_esign_pdf](addons_token/amr_esign_pdf).
