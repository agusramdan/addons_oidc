# Modul `amr_resource`

## Untuk Developer

### 1. Arsitektur
Modul `amr_resource` adalah fondasi dasar (core resource server) untuk mengamankan dan memvalidasi akses resource Odoo melalui JSON Web Token (JWT) atau token introspeksi OAuth2/OIDC. Modul ini memperluas `ir.http` untuk menyediakan mekanisme autentikasi kustom berbasis token, serta menyediakan helper methods bagi modul-modul lain (seperti `amr_data_sync`, `amr_service_client`, dll) untuk melakukan validasi token dan komunikasi antar service.

### 2. Model, Field, dan Relasi
- **`amr.resource.helper`** (AbstractModel):
  - Berisi method utilitas untuk manajemen token, verifikasi issuer, audience, integrasi dengan OIDC endpoint (`/.well-known/openid-configuration`, `/.well-known/jwks.json`), validasi token HS/RS, serta pencocokan user (`res.users`).
- **`res.users`** (Model Extension):
  - Menambahkan method pengecekan grup/peran (`is_user_machine`, `is_user_technical`, `is_user_business`, `is_user_allow_create_token`).
  - Menambahkan method `decode`, `with_access_token_context`, dll.
- **`res.config.settings`** (TransientModel Extension):
  - Menyediakan konfigurasi parameter sistem (`amr_resource.issuer`, `amr_resource.audience`, `web.base.url.freeze`, serta toggles untuk modul-modul `amr_*` lainnya).
- **`create.user.wizard`** (TransientModel):
  - Wizard untuk membuat user baru berdasarkan template user yang sudah ada (menyalin grup dan atribut `share`).

### 3. Cara Modul Lain Memakainya
Modul seperti `amr_data_sync` dan service client bergantung penuh pada `amr_resource`.
Contoh pemanggilan helper dari modul lain:
```python
# Validasi token secara programatik
payload = self.env['amr.resource.helper'].validate(token)
uid = self.env['amr.resource.helper'].get_uid(payload)
```
Atau menggunakan auth method di Controller:
```python
@route('/api/v1/endpoint', type='http', auth='machine', methods=['POST'], csrf=False)
def my_api(self, **kwargs):
    # request.uid dan request.jwt_payload otomatis di-set oleh _auth_method_machine
    pass
```

### 4. API / Method Publik
- **`amr.resource.helper`**:
  - `validate(token)`: Memvalidasi JWT (mendukung algoritma HS via introspection atau RS via JWKS).
  - `get_user_match(validation)`: Mencocokkan payload token dengan `res.users` berdasarkan email atau login (`sub`).
  - `get_bearer_token()`: Mengambil token dari header `Authorization: Bearer <token>`.
- **Controllers (`RedirectController`, `JsonRpcApi`)**:
  - `/redirect`: Redirect ke URL dengan menyertakan token akses.
  - `/api/v1/access_token/url`: Endpoint untuk menghasilkan URL akses dengan token.
  - `/api/test/connection/machine`: Endpoint tes koneksi dengan auth method `machine`.
  - `/api/dataset/call_kw`: JSON-RPC endpoint yang diamankan dengan auth `machine` untuk pemanggilan method model secara jarak jauh.

### 5. Koneksi & Autentikasi Antar Service
- Menggunakan skema autentikasi HTTP Bearer Token (`auth='machine'` atau `auth='user_or_param'`).
- Memvalidasi token dengan melakukan introspeksi ke token endpoint atau verifikasi cryptographic menggunakan Public Keys (JWKS) dari OIDC Provider.

### 6. Error Handling
- Didefinisikan di `exceptions.py` dengan class `APIException` dan helper `handle_exception(e)` yang mengembalikan respons JSON standar berisi `error` dan `error_description` beserta status HTTP yang sesuai (misal: 400, 401, 500).

### 7. Contoh Kode Nyata dari Repo
Penggunaan auth method `machine` pada `ir.http.py`:
```python
@classmethod
def _auth_method_machine(cls):
    helper = request.env['amr.resource.helper'].sudo()
    token = helper.get_bearer_token()
    validate = helper.get_validate_user(token)
    if not validate:
        raise Unauthorized('Invalid token')
    user = helper.get_user_match(validate)
    if not user:
        raise Unauthorized('User not found')
    if request.uid != user.id:
        request.uid = user.id
        request.jwt_token = token
        request.jwt_payload = validate
```

### 8. Catatan Pola Odoo 13 vs 20
- Pada Odoo 13, manajemen session dan pembaruan `request.uid` / `request.session` dilakukan secara langsung melalui manipulasi `request.uid` dan `session.session_token` di dalam `ir.http`. Komentar dalam kode menunjukkan penyesuaian eksplisit untuk kompatibilitas environment Odoo versi lebih tinggi/rendah.

---

## Untuk User

### 1. Menu & Form UI
- **Settings > General Settings > Amr OIDC / Resource Server**: Menu konfigurasi utama untuk mengatur Issuer, Audience, serta mengaktifkan modul-modul integrasi `amr_*` lainnya.
- **Users / Wizards**: Menu untuk membuat user khusus mesin/service menggunakan *Create User Wizard*.

### 2. Alur Harian
- Administrator sistem mengonfigurasi URL Issuer dan Audience pada menu Settings.
- Membuat akun *machine/service user* menggunakan wizard agar service eksternal dapat terhubung ke Odoo menggunakan token JWT yang valid.

### 3. Konfigurasi
- **Issuer**: Menentukan base URL OIDC issuer yang dipercaya.
- **Audience**: Menentukan target audiens token untuk validasi keamanan.
- **Freeze Web Base URL**: Mencegah Odoo mengubah `web.base.url` secara otomatis.

### 4. FAQ
- **Q: Mengapa API mengembalikan error 401 Unauthorized?**
  - A: Pastikan header `Authorization: Bearer <token>` disertakan dengan benar dan token belum kedaluwarsa atau issuer/audience sesuai dengan konfigurasi sistem.
- **Q: Bagaimana cara membuat user untuk koneksi mesin antar service?**
  - A: Gunakan menu *Create User Wizard* dan pastikan user tersebut masuk ke grup Machine yang disediakan oleh modul.
