# Modul `amr_service_client` — Client untuk Resource Server OIDC

> **Peran dalam suite:** Addon **klien resmi** untuk memanggil **Resource Server** (`amr_resource`). Modul ini adalah satu-satunya cara yang benar bagi modul lain (`amr_data_sync`, dsb.) untuk melakukan panggilan HTTP/JSON-RPC ke service yang dilindungi token — autentikasi ditangani otomatis via *Auth Provider*, tanpa memegang token manual.

| | |
|---|---|
| Versi | 13.0.0.1.0 |
| Depends | `base`, `amr_resource` (resource server yang dipanggil) |
| Maintainer | Agus Muhammad Ramdan |
| Status migrasi 20 | Belum dimulai |

---

## Untuk Developer

### 1. Arsitektur — pola Client ↔ Resource Server

```
┌──────────────────────────────────────────────────────┐
│ MODUL PEMAKAI (mis. amr_data_sync)                   │
│   client = env['service.client'].with_context(...)   │
│   client.get('/api/v1/...')                          │
└──────────────┬───────────────────────────────────────┘
               │ 1. endpoint.get_url(path)
               │ 2. credential → AuthProvider.authenticate()
               │    (Bearer/JWT ditambahkan otomatis; audience
               │     diambil dari endpoint.audience)
               ▼
┌──────────────────────────────────────────────────────┐
│ RESOURCE SERVER (Odoo lain dengan amr_resource)      │
│   ir.http auth='machine' → validate token → resource │
└──────────────────────────────────────────────────────┘
```

Komponen:

| Komponen | Fungsi |
|---|---|
| `service.endpoint` (+ mixin `service.endpoint.mixin`) | Definisi endpoint: base URL (sumber: value / env / odoo config / system parameter), `base_path` (mis. `/api/v1`), `audience`, `credential_id`, `timeout` (default 30), `content_type_default`, `active_log` |
| `service.credential` + `service.credential.loader` | Kredensial & cara muat: Database, File Path, Env JSON/Path, Config Path, System Parameter JSON/Path |
| `service.auth.factory` → Auth Provider | Menambahkan autentikasi ke request context (Bearer/JWT ke resource server) |
| `service.client` (`ServiceClient`) | Eksekusi HTTP: `get/post/put/delete`, normalisasi JSON (`normalize_json`: datetime/Decimal/UUID/bytes → serializable) |
| `service.client.log` | Riwayat request/response (`active_log`), mendukung re-send async (`dispatch_send`) |
| `RemoteObjectProxy` | Memanggil `call_kw` Odoo remote seolah objek lokal (`/api/dataset/call_kw`) |
| `ir.actions.server` (state `service_client`) | Server Action bisa memicu panggilan HTTP langsung |

### 2. Contoh Pemakaian (dari kode)

```python
# 1) Dapatkan client (endpoint + credential dikonfigurasi dari UI)
client = env['service.client'].create_client(endpoint)  # via factory

# 2) Panggilan REST sederhana — Bearer token auto-attach
resp = client.get('/api/v1/partners', params={'domain': '[]'})
resp.raise_for_status()
data = resp.json()

# 3) JSON-RPC call_kw ke Odoo resource server (RemoteObjectProxy)
with RemoteObjectProxy(client, 'res.partner', fields=['name']) as proxy:
    hasil = proxy.search_read(domain=[('customer_rank', '>', 0)], limit=10)
```

### 3. Konfigurasi Endpoint (UI)

- URL bisa diambil dari: **Value** langsung, **OS Environment**, **Odoo Config**, atau **System Parameter** (`config_param_name`) — fleksibel untuk multi-environment
- `audience` wajib cocok dengan `amr_resource.audience` di sisi resource server
- `timeout` default 30 detik; `active_log` untuk audit request/response

### 4. Error Handling
- `resp.raise_for_status()` di tiap panggilan
- JSON-RPC `error` → `RuntimeError`
- Log request/response tersimpan (`service.client.log`) untuk investigasi + `dispatch_send` untuk kirim ulang async

### 5. Catatan Pola Odoo 13 vs 20
- Model mixin + factory pattern aman; pastikan `ir.actions.server` state tambahan tetap terdaftar
- `normalize_json` memakai `fields.Datetime.to_string` — cek di 20 masih tersedia

---

## Untuk User

### Konfigurasi Awal
1. **Service → Endpoints** — buat endpoint: isi base URL resource server (mis. `https://odoo-cantik.example.com`), base path (mis. `/api/v1`), audience, credential
2. **Service → Credentials** — simpan kredensial (client_id/secret atau kunci) pilih sumber penyimpanan aman
3. Aktifkan **log** bila ingin audit panggilan

### Pemakaian Harian
- Modul bisnis otomatis memakai endpoint ini — tidak ada input manual per transaksi
- Cek **log** bila ada kegagalan integrasi; gunakan *re-send* untuk mengirim ulang yang gagal

### FAQ
- **401 dari resource server?** Audience di endpoint ≠ `amr_resource.audience` di server, atau credential kadaluarsa
- **Timeout?** Naikkan `timeout` endpoint, atau cek kesehatan resource server

---

## Catatan Versi
- Odoo sumber: 13.0.1.0
- Status migrasi 20.0: **Belum dimulai**
