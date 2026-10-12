# Modul `amr_service_client`

## Untuk Developer

### 1. Arsitektur Client-Server & Desain Pola
Modul `amr_service_client` adalah *general-purpose HTTP client & JSON-RPC bridge* untuk Odoo yang dirancang untuk berkomunikasi secara aman dengan *Resource Server* atau *Application Server* lain (terintegrasi erat dengan modul `amr_resource` dan `amr_data_sync`). 
- **Arsitektur:** Menggunakan pola *Client-Provider-Loader*. Modul memisahkan definisi endpoint, pengelolaan kredensial/autentikasi, serta eksekusi request HTTP/JSON-RPC melalui *Service Client Factory*.
- **Komponen Utama:**
  - `service.endpoint` (extends `service.endpoint.mixin`): Menyimpan konfigurasi URL tujuan, base path, timeout, default content-type, log toggle, dan relasi kredensial. Mendukung resolusi URL dari *Value*, *OS Environment*, *Odoo Config*, atau *System Parameter*.
  - `service.credential`: Mengelola metode autentikasi dan penyimpanannya (Database, File Path, Env JSON/Path, Config Path, System Parameter JSON/Path).
  - `service.client` (`ServiceClientFactory` & `ServiceClient`): Kelas utama pembungkus `requests` yang menangani serialisasi JSON (`normalize_json`), autentikasi otomatis via *Auth Provider*, serta proxy objek remote (`RemoteObjectProxy`).
  - `service.client.log`: Menyimpan riwayat log request/response (mendukung asynchronous re-send via `dispatch_send`).
  - `ir.actions.server`: Menambahkan aksi server kustom `state='service_client'` agar Odoo Server Actions dapat langsung memicu panggilan HTTP/JSON-RPC ke service eksternal.

---

### 2. Model, Field, dan Relasi Lengkap

#### A. `service.endpoint` (`service.endpoint.mixin`)
- `name` (Char, Required): Nama deskriptif endpoint.
- `code` (Char, Required, Indexed): Kode unik pengenal endpoint (digunakan oleh modul lain seperti `amr_data_sync` untuk pencarian instan).
- `base_url` / `url` (Computed Char): URL akhir hasil komputasi dari sumber (`source`) dan path.
- `source` (Selection: `value`, `env`, `config`, `config_parameter`): Sumber penentuan URL.
- `config_param_name` (Char): Nama key config parameter / env variable jika source bukan value langsung.
- `base_path` (Char): Prefix path tambahan (misal `/api/v1`).
- `audience` (Char): Target audience token OAuth2/OIDC.
- `credential_id` (Many2one -> `service.credential`): Kredensial default yang terikat ke endpoint.
- `timeout` (Integer): Batas waktu request dalam detik (default 30).
- `active` (Boolean): Status aktif endpoint.
- `active_log` (Boolean): Flag untuk mengaktifkan logging otomatis pada setiap pemanggilan.

#### B. `service.credential`
- `name` (Char, Required): Nama kredensial.
- `source` (Selection: `database`, `file_path`, `env_json`, `env_path`, `config_path`, `system_parameter_json`, `system_parameter_path`): Sumber penyimpanan data kredensial.
- `reference` (Char): Path file atau key parameter/env.
- `credential_json` (Text): Payload JSON mentah jika disimpan di database.
- `scopes` (Char): Daftar scope yang dipisahkan spasi/koma.

#### C. `service.client` (`ServiceClientFactory` Model)
- `name` (Char): Nama konfigurasi client.
- `model_id` (Many2one -> `ir.model`): Target model Odoo tempat action dieksekusi.
- `endpoint_id` (Many2one -> `service.endpoint`): Endpoint tujuan.
- `credential_id` (Many2one -> `service.credential`): Kredensial spesifik client.
- `active_log` (Boolean): Toggle log.
- `each_record` (Boolean): Eksekusi per record vs recordset utuh.
- `iteration` (Text): Python code untuk menghasilkan konteks iterasi.
- `code` (Text): Python code utama untuk membangun payload/parameter.
- `handle` (Text): Python code untuk menangani/memproses response.
- `payload_ids` (One2many -> `service.client.payload`): Parameter payload terstruktur (Fixed, Expression, Random Int).

#### D. `service.client.payload`
- `key` (Char): Key payload JSON.
- `value` (Text): Nilai atau ekspresi Python/eval string (`${...}`).
- `type` (Selection: `fix`, `exp`, `random_int`).
- `service_client_id` (Many2one).

#### E. `service.client.log`
- `state` (Selection: `outgoing`, `done`, `error`): Status pengiriman.
- `endpoint_id`, `credential_id`, `client_id` (Many2one relasi pendukung).
- `request_context` (Text): JSON dump konteks request (headers, url, payload, params).
- `response` (Text): Isi respons dari server atau traceback error.

---

### 3. Konfigurasi Koneksi ke Service Eksternal
1. **Endpoint Configuration (`service.endpoint`)**:
   - Tentukan Nama & Kode unik (misal: `helpdesk_server`).
   - Pilih *Source* URL (`value` untuk hardcode URL, atau `config_parameter` / `env` untuk dinamis).
   - Masukkan Base URL (misal: `https://helpdesk.agusramdan.web.id`) dan *Base Path* (`/api/v1`).
2. **Credential Configuration (`service.credential`)**:
   - Tentukan tipe auth dan sumber penyimpanan. Wizard `service.credential.wizard` tersedia di UI untuk mempermudah pembuatan template JSON kredensial (`service_account`, `client_secret`, `api_key`, `bearer`, `basic`).

---

### 4. Cara `amr_data_sync` Memanggilnya (Contoh Kode Nyata)
Modul `amr_data_sync` menggunakan `service.client` melalui `ServerSync` (`external.server.sync` yang mewarisi `service.endpoint.mixin`) untuk melakukan sinkronisasi data dua arah via JSON-RPC `call_kw` atau endpoint REST:

```python
# Contoh nyata dari amr_data_sync (data_sync_strategy.py & data_sync_server.py)
def sync_list_model_object(self):
    self_internal = self.ensure_internal_context()

    def callback(item, **kwargs):
        self_internal.env['external.data.sync'].data_from_external(item, self_internal)

    kwargs = self.prepare_sync_list_dict() or {}
    
    # Memanggil create_remote_model yang membungkus service.client.get_remote_object
    with self.server_sync_id.create_remote_model(self.external_model, **kwargs) as ModelObject:
        ModelObject.external_data_callback(callback)
```

Di balik layar, `create_remote_model` memanggil factory pada `amr_service_client`:
```python
def create_remote_model(self, external_model, **kwargs):
    return self.env['service.client'].get_remote_object(self, external_model, **kwargs)
```
Dan pemanggilan method jarak jauh (misal `search_read` / `call`) diterjemahkan oleh `RemoteObjectProxy` menjadi request JSON-RPC ke `/api/dataset/call_kw` di server tujuan.

---

### 5. API / Method Publik & Klien

#### Kelas `ServiceClient` (`services/service_client.py`):
- `call(method, path, params=None, payload=None, headers=None, audience=None)`: Mengirim HTTP request umum (`GET`, `POST`, `PUT`, `DELETE`).
- `get(path, params=None, **kwargs)` / `post(path, payload=None, **kwargs)` / `put(...)` / `delete(...)`: Helper method HTTP shorthand.
- `prepare_payload(**payload)`: Menyiapkan dispatch dengan log otomatis.

#### Kelas `RemoteObjectProxy` (Odoo RPC Proxy):
- Memungkinkan pemanggilan method model remote seolah-olah model lokal:
  ```python
  with env['service.client'].get_remote_object('service_endpoint_code', 'res.partner') as Partner:
      partners = Partner.search_read([('customer', '=', True)], fields=['name', 'email'])
  ```
- Method yang didukung: `search_read`, `read`, `search_count`, dan pemanggilan method apa pun via `__getattr__` (`__call__` ke `/api/dataset/call_kw`).

#### Model `ServiceClientFactory` (`service.client`):
- `get_service_client(service_code, credential=None, path=None, method=None)`
- `get_remote_object(service_code, model_name, credential=None, **kwargs)`
- `call(...)`, `get(...)`, `post(...)`, `put(...)`, `delete(...)`

---

### 6. Autentikasi Antar Service (JWT / Token — Kaitkan dengan `amr_resource`)
Modul ini mendukung 5 provider autentikasi utama melalui `service.auth.factory` (`services/providers.py`):
1. **`api_key` (`ApiKeyProvider`)**: Menyertakan header kustom (default `X-API-Key`).
2. **`bearer` (`BearerProvider`)**: Mengirim token statis `Authorization: Bearer <token>`.
3. **`basic` (`BasicProvider`)**: Mengirim kredensial Basic Auth base64 (`username:password`).
4. **`client_secret` (`ClientSecretProvider`)**: Mengambil token dinamis dari OIDC Token Endpoint menggunakan `grant_type=client_credentials`. Dilengkapi mekanisme *Token Cache* (`service.token.cache`) untuk menghindari request token berlebihan sebelum TTL kedaluwarsa.
5. **`service_account` (`ServiceAccountProvider`)**: Autentikasi tingkat lanjut menggunakan JWT Assertion (RFC 7523) dengan `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer` yang ditandatangani menggunakan private key RSA/ECDSA (`RS256`, dll.), yang divalidasi langsung oleh server penerima berbasis modul `amr_resource`.

---

### 7. Error Handling & Retry
- **Request Exception Handling**: Setiap pemanggilan `requests.request` dibungkus dalam blok `try...except (requests.RequestException, Exception)`.
- **Logging Otomatis ke DB**: Jika request gagal (`state='error'`), trace error dan respon mentah otomatis dicatat ke tabel `service.client.log` beserta konteks request-nya, memungkinkan administrator melakukan *Resend* manual (`dispatch_send()`).
- **JSON-RPC Error**: Respons JSON-RPC yang mengandung key `"error"` akan memunculkan exception `RuntimeError` (`Odoo login error: ...`).

---

### 8. Catatan Pola Odoo 13 vs 20
- **Odoo 13 Environment & Context**: Modul ini dirancang kompatibel penuh dengan struktur ORM Odoo 13 (`self.env`, `sudo()`, `ensure_one()`), namun dioptimalkan agar kompatibel dengan standar pemanggilan API Odoo modern (Odoo 16/17/20) melalui struktur modular *Service Providers* dan *Payload Normalizer* (`normalize_json` menangani UUID, datetime, decimal, binary).
- **Server Actions Integration**: Integrasi `ir.actions.server` menggunakan `selection_add=[("service_client", "Service Client")]`, mengikuti pola ekstensi server action standar Odoo yang aman di-upgrade ke versi Odoo yang lebih tinggi.

---

## Untuk User

### 1. Konfigurasi Koneksi Service dari UI
Administrator dapat mengonfigurasi integrasi antar service langsung melalui antarmuka Odoo:
- **Menu Utama**: `Settings > Technical > Integration` (atau menu *Integration* yang tersedia).
  - **Endpoints (`service.endpoint`)**: Menentukan URL server tujuan, kode unik, timeout, dan kredensial default. Terdapat tombol aksi **Test Endpoint** (`service.endpoint.test.wizard`) untuk menguji koneksi secara langsung dari UI.
  - **Credentials (`service.credential`)**: Mengelola metode autentikasi (API Key, Bearer, Client Secret, Service Account). Terdapat **Config Credential Wizard** (`service.credential.wizard`) untuk membantu menghasilkan format JSON kredensial yang valid serta tombol **Test Credential** untuk memvalidasi koneksi token.
  - **Client (`service.client`)**: Mengatur skrip Python dinamis, pemetaan payload, dan pemanggilan layanan otomatis.
  - **Integration Logs (`service.client.log`)**: Memantau riwayat log pengiriman request dan respons server (berisi status *Done* atau *Error*, serta tombol untuk mengirim ulang/resend).

---

### 2. Monitoring Status Koneksi
- **Log Integrasi**: Setiap kegagalan koneksi atau error HTTP akan tercatat secara otomatis di menu **Integration Log**. User dapat melihat detail error, payload request, dan response teks untuk keperluan audit.
- **Wizard Uji Koneksi**:
  - Gunakan form **Test Endpoint** untuk mengirim uji coba HTTP method (`GET`, `POST`, dll.) ke path tertentu dan melihat kode status HTTP serta respons JSON secara langsung.
  - Gunakan tombol **Test Credential** pada form Credential untuk memastikan token/kredensial berhasil diautentikasi oleh server eksternal.

---

### 3. FAQ (Frequently Asked Questions)

- **Q: Mengapa koneksi service mengembalikan error timeout atau tidak dapat terhubung?**
  - A: Periksa kembali konfigurasi *Base URL* pada menu *Endpoints*, pastikan jaringan/firewall mengizinkan komunikasi ke server tersebut, dan sesuaikan nilai *Timeout* jika server eksternal lambat merespons.
- **Q: Bagaimana cara mengatasi error autentikasi token pada Service Account / Client Secret?**
  - A: Pastikan URL *Token URI*, *Client ID*, dan *Private Key* / *Client Secret* sudah benar. Gunakan tombol **Test Credential** untuk memverifikasi apakah token OAuth2 berhasil diterbitkan oleh OIDC provider.
- **Q: Di mana saya bisa melihat log request yang gagal terkirim?**
  - A: Buka menu `Integration > Integration Logs`. Anda dapat memfilter log berdasarkan status *Error*, melihat isi payload, dan melakukan *Resend* (kirim ulang) setelah masalah diperbaiki.
- **Q: Apakah modul ini mendukung pemanggilan RPC antar instance Odoo?**
  - A: Ya, melalui `RemoteObjectProxy` yang otomatis membungkus komunikasi ke endpoint JSON-RPC `/api/dataset/call_kw` di server tujuan dengan pengamanan token JWT dari `amr_resource`.

*ponytail: ceiling=mendukung REST dan Odoo JSON-RPC standar; upgrade path=tambahkan dukungan gRPC/GraphQL client jika diperlukan di masa depan.*
