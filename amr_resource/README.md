# Modul `amr_resource` — Resource Server OIDC

> **Peran dalam suite:** Addon **dasar** OIDC yang mengubah Odoo menjadi **Resource Server** — menerima & memvalidasi *access token* (JWT / opaque) sebelum resource dilayani. Semua modul lain (`amr_data_sync`, `amr_service_client`, controller API custom) berpijak pada helper modul ini.

| | |
|---|---|
| Versi | 13.0.0.0.8 |
| Depends | `base`, `web`, `base_setup` |
| Maintainer | Agus Muhammad Ramdan |
| Status migrasi 20 | Belum dimulai |

---

## Untuk Developer

### 1. Arsitektur

Modul menempel pada 3 titik Odoo:

```
┌─────────────────────────────────────────────────────┐
│ ir.http (AbstractModel, _inherit)                   │
│  → auth_method 'machine': Bearer token di-          │
│    extract → amr.resource.helper.validate() →       │
│    get_user_match() → session dibuat (set_session)  │
├─────────────────────────────────────────────────────┤
│ amr.resource.helper (AbstractModel)                 │
│  → inti validasi: decode/introspect, jwks, issuer,  │
│    audience, user matching                          │
├─────────────────────────────────────────────────────┤
│ res.config.settings (res.users extension)           │
│  → konfigurasi issuer/audience, grup machine/       │
│    technical/business, wizard create user           │
└─────────────────────────────────────────────────────┘
```

Controller API cukup mendeklarasikan `auth='machine'` — `ir.http` otomatis memvalidasi token sebelum request masuk.

### 2. Model & Method Inti (`models/helper.py` — `amr.resource.helper`)

**Konfigurasi (ir.config_parameter):**
- `amr_resource.issuer` — issuer OIDC (default: `web.base.url`)
- `amr_resource.audience` — audience yang diterima

**Discovery & keys:**
- `get_oidc_config(issuer)` → fetch `/.well-known/openid-configuration`
- `get_jwks_data(issuer)` → fetch `/.well-known/jwks.json`

**Token lifecycle:**

| Method | Fungsi |
|---|---|
| `generate_token(client_id, client_secret, issuer, **kw)` | POST ke `token_endpoint` IdP → access token (client-credentials) |
| `encode(**kw)` | shortcut `generate_token()['access_token']` |
| `decode(token)` | alias `validate(token)` |
| `is_local_token(token)` | cek apakah `iss` == `web.base.url` |
| `validate_hs(token)` | HS-signed → **introspection endpoint** (butuh `active: true`) |
| `validate(token)` | RS-signed → PyJWKClient ambil signing key dari `jwks_uri` → `jwt.decode(alg, issuer, audience)` |

**User matching (`get_user_match`)** — urutan pencarian `res.users`:
1. `email` → `login` ATAU `email`
2. `sub` → `login`
3. token `type=machine` → cari termasuk user non-aktif

**Ekstraksi token dari request (`get_param_token` / `get_header_token` / `get_bearer_token`):**
- header `Authorization: Bearer <token>` (RFC 6750)
- header `access_token` / `token`
- query/form: `access_token`, `token`, `token_access`

### 3. Cara Modul Lain Memakainya

```python
# Validasi token → payload claims
payload = self.env['amr.resource.helper'].validate(token)

# Payload → uid (user matching)
uid = self.env['amr.resource.helper'].get_uid(payload)

# Controller: cukup pakai auth='machine' (ir.http menangani)
@route('/api/v1/endpoint', type='http', auth='machine', csrf=False)
def my_api(self, **kw): ...

# Client-credentials: minta token dari IdP
resp = self.env['amr.resource.helper'].generate_token(
    client_id='x', client_secret='y', issuer='https://oidc.example.com',
    grant_type='client_credentials')
```

Konsumen: `amr_data_sync` (validasi request sinkronisasi), `amr_service_client` (autentikasi antar service), `amr_token`.

### 4. Error Handling

`exceptions.py` mendefinisikan exception khusus; validasi gagal → 401 Unauthorized via `ir.http`; `validate_hs` raise `InvalidTokenError` bila token tidak `active`.

### 5. Catatan Pola Odoo 13 vs 20
- `request.session` handling berubah sejak 16 (`ir_http.py` sudah ada komentar — perlu review saat migrasi)
- `PyJWKClient` dari `pyjwt>=2` — pastikan versi di requirements Odoo 20
- `auth='machine'` harus tetap terdaftar di `_auth_method_map`

---

## Untuk User

### Konfigurasi Awal
1. **Settings → General Settings → amr_resource** — isi Issuer (URL IdP, mis. `https://oidc.agusramdan.web.id/application/o/rancan-website/`) dan Audience
2. IdP harus mengekspos `/.well-known/openid-configuration` & `jwks.json`

### Cara Kerja Singkat
API dikirim request dengan header `Authorization: Bearer <token>` → Odoo memvalidasi token ke IdP (via JWKS atau introspection) → user dicocokkan (email/sub) → resource dilayani bila valid.

### FAQ
- **Token ditolak "not active"?** Token HS-signed — pastikan introspection endpoint tersedia di IdP.
- **User tidak tercocok?** Pastikan email di IdP = login/email user Odoo, atau token `type=machine` untuk service account.

---

## Catatan Versi
- Odoo sumber: 13.0.0.0.8
- Status migrasi 20.0: **Belum dimulai**
