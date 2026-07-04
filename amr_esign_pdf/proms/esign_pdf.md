Buat addon Odoo 13 bernama `amr_esign_pdf` di `../` untuk mendukung PDF Multiple Signature (PAdES).
Addon ini dignunakan sebagai store infomasi pdf document yang di sing oleh internal atau provider lain.
Walau pun demikian untuk keperluan internal (provider internal) maka.
Untuk worklow engine akan di handle pada modul yang lain misalkan (amr_approval)

Definision:
- PEM (Privacy-Enhanced Mail) adalah format Base64 yang dibungkus dengan header dan footer.
- Odoo menggunakan Controller untuk menerima rest api (Text di convert menjadi json) type="http" auth="machine".
  - Payload (Text di convert menjadi json)  
  - Response (JSON)
    - status (Char)
    - data (Dictionay or List)
- Service adalah model.Abstract untuk menyimpan fungsi atau method yang dipanggil dari controller
- Spesifikasi resmi mengenai /ByteRange terdapat pada standar PDF:
  - ISO 32000-1:2008 (PDF 1.7), bagian Digital Signatures.
  - ISO 32000-2:2020 (PDF 2.0), Section 12.8.3.3 - CMS (PKCS #7) signatures
- Contoh signature block
---
/Type /Sig
/Filter /Adobe.PPKLite
/SubFilter /adbe.pkcs7.detached
/ByteRange [0 840 960 240]
/Contents <3082....>
---

Spesifikasi:

Model `pdf.document`:
- `name` (Char, readonly when `state` not in draft)
- `state` (Selection: draft, request, signed)
- `provider` (Selection: internal  , readonly when `state` not in draft) -> CA Provider
- `pdf_file` (Binary, readonly when `state` not in draft, filename `pdf_filename`) -> pdf source
- `pdf_signature_block` (Text, readonly)  → value yang akan di sisipkan di pdf source
- `pdf_byte_range`(Char, readonly) Format PDF Byte range untuk perhitungan PDF range
- `pdf_hash` (Char, readonly) → hash dari PDF untuk request CMS
- `pdf_lock` (Binary , readonly) → PDF dengan placeholder dan signature block ruang signature
- `signed_pdf` (Binary, readonly,  filename `signed_pdf_filename`)

Model `pdf.sign`:
- `name` (Char)
- `is_internal` (Boolean compute dari ca_provaider == internal)
- `pdf_document_id` (Many2one ke `pdf.document`)
- `user_id` (Many2one ke `res.users`)
- `partner_id` (Many2one ke `res.partner`)
- `signature_index` (Integer) atau `signature_name`
- `cms_data` (Binary, CMS hasil CA)
- `state` (Selection: draft, requested, signed)

Model `user.ca.data`:
- `name` (Char)
- `user_id` (Many2one ke `res.users`)
- `serial_number` (Char  serial_number )
- `algorithm` (Selection: ref from  https://pyjwt.readthedocs.io/en/stable/algorithms.html )
- `certificate` (Text PEM format)
- `private_key` (Text PEM format) 
- `public_key` (Text PEM format)
- `state` (Selection: draft, active, signed)

Wizard `user.ca.data.wizard` generate self signed ca:
- `user_id` (Many2one ke `res.users`)
- `algorithm` (Selection: ref from  https://pyjwt.readthedocs.io/en/stable/algorithms.html )
- `name` (Char use user_id.name when empty)
- `org_name` (Char  default="Odoo ESign PDF" )
- `validity_days` (Integer ('Validity (days)', default=365))
- `serial_number` (Char  serial_number, readonly saat tombol generate di tekan )
- `certificate` (Text PEM format , readonly saat tombol generate di tekan)
- `private_key` (Text PEM format , readonly saat tombol generate di tekan) 
- `public_key` (Text PEM format , readonly saat tombol generate di tekan)    

Controller Path '/api/v1/document/submit' methods="POST" :
  Payload :
  - `name`
  - `provider`
  - `pdf_file`  

Fitur:

- Tambahkan tombol untuk:
  - `Prepare Signature` / `Request CMS`
  - `Apply CMS`
  - `Reset`
- Upload PDF pada `pdf.document`
- Prepare Signature melakukan Prepare Signature dictionary dengan tahapan berkut
  - Siapkan signature block dan simpan dalan pdf_signature_block sebagai
  - Tentukan ByteRange dan simpan dalam `pdf_byte_range`
  - Ambil data byte dan Hitung hash PDF dan simpan di `pdf_hash` jangan menggunakan compute
  - Generate / simpan `pdf_lock` dengan ruang CMS untuk signature berikutnya
  - set status menjadi requested
  - selain status draft pdf_file tidak bisa di edit
- Request CMS ke CA menggunakan `pdf_hash`
- Simpan `cms_data` di `pdf.sign`
- Tambahkan tombol `Sign pdf` Untuk Generate `signed_pdf` setelah semua `pdf.sign` mempunyai signed.
- Model `user.ca.data` Master data untuk generate CMS dengan parameter pdf_hash
- Wizard `user.ca.data.wizard` generate  data `user.ca.data` oleh administrator .  action_create_ca_data mempunyai feature create  ca_private_key dan ca_certificate berdasarkan alogitma tertentu .
- tambahkan action signed pada model `pdf.sign` yang akan di trigger user.

Views & menu:
- Form view + tree view untuk `pdf.document`
- Form view + tree view untuk `pdf.sign`
- Form view + tree view untuk `user.ca.data`
- Menu item dan action `ir.actions.act_window` pisahkan menu pada file menuitem.xml

Security:
- Tambahkan `security/ir.model.access.csv` untuk akses user

Manifest:
- Buat `__manifest__.py` dengan urutan: `name`, `version`, `category`, `summary`, `description`, `author`, `website`, `license`, `depends`, `data`, `demo`, `assets`, `installable`, `auto_install`, `application`, `externaldepenency`

Tambahkan _logger error setelah exception
Implementasi logika PAdES nyata menggunakan pyHanko (mencakup: prepare lock, calculate ByteRange, generate hash, apply CMS, incremental updates).


simpan views dan xml wizard pada direktory wizard

Catatan: gunakan ORM Odoo, hindari raw SQL, dan jangan letakkan business logic di controller. Ikuti standar Odoo 13 / OCA.

buatkan tests case untuk addons ini.
