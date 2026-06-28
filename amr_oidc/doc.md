
# OAuth 2.0 & OpenID Connect API Documentation

## Overview

Implementasi ini menyediakan layanan **OAuth 2.0** dan **OpenID Connect (OIDC)** untuk autentikasi dan otorisasi aplikasi. Endpoint OIDC berada di bawah prefix `/oidc/`, sedangkan metadata OpenID Connect dan JSON Web Key Set (JWKS) dipublikasikan melalui endpoint `.well-known` sesuai spesifikasi OpenID Connect Discovery.

---

# Base URL

```
https://intra.cerindocorp.id
```

---

# Endpoint Summary

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/.well-known/openid-configuration` | OpenID Connect Discovery |
| GET | `/.well-known/jwks.json` | JSON Web Key Set (JWKS) |
| GET | `/oidc/authorize` | Authorization Endpoint |
| POST | `/oidc/token` | Token Endpoint |
| POST | `/oidc/introspect` | Token Introspection |
| GET | `/oidc/userinfo` | User Information |

---

# OpenID Connect Discovery

Retrieve the OpenID Connect provider metadata.

## Request

```http
GET /.well-known/openid-configuration
```

## Response

```json
{
  "issuer": "https://intra.cerindocorp.id",
  "authorization_endpoint": "https://intra.cerindocorp.id/oidc/authorize",
  "introspection_endpoint": "https://intra.cerindocorp.id/oidc/introspect",
  "token_endpoint": "https://intra.cerindocorp.id/oidc/token",
  "userinfo_endpoint": "https://intra.cerindocorp.id/oidc/userinfo",
  "jwks_uri": "https://intra.cerindocorp.id/.well-known/jwks.json",
  "response_types_supported": [
    "code",
    "token",
    "id_token"
  ],
  "subject_types_supported": [
    "public"
  ],
  "id_token_signing_alg_values_supported": [
    "HS512"
  ],
  "scopes_supported": [
    "openid",
    "profile",
    "email"
  ],
  "token_endpoint_auth_methods_supported": [
    "client_secret_post",
    "client_secret_basic"
  ],
  "claims_supported": [
    "uid",
    "db",
    "user_id",
    "sub",
    "name",
    "email"
  ]
}
```

---

# Authorization Endpoint

Generates an authorization code after successful user authentication.

## Request

```http
GET /oidc/authorize
```

### Query Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| response_type | Yes | `code` |
| client_id | Yes | OAuth Client ID |
| redirect_uri | Yes | Registered Redirect URI |
| scope | Yes | Requested scopes |
| state | Recommended | CSRF protection |
| nonce | Recommended | Required for OIDC |

### Example

```http
GET /oidc/authorize?
response_type=code&
client_id=my_client&
redirect_uri=https://client.example.com/callback&
scope=openid profile email&
state=abc123&
nonce=random123
```

---

# Token Endpoint

Exchanges an authorization code for an Access Token and ID Token.

## Request

```http
POST /oidc/token
Content-Type: application/x-www-form-urlencoded
```

### Authorization Code Grant

```text
grant_type=authorization_code
code=xxxxxxxx
client_id=my_client
client_secret=xxxxxxxx
redirect_uri=https://client.example.com/callback
```

### Example Response

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "eyJ...",
  "id_token": "eyJ..."
}
```

---

# UserInfo Endpoint

Returns information about the authenticated user.

## Request

```http
GET /oidc/userinfo
Authorization: Bearer ACCESS_TOKEN
```

## Example Response

```json
{
  "sub": "123",
  "uid": "agus",
  "user_id": 7,
  "db": "production",
  "name": "Agus Muhammad Ramdan",
  "email": "agus@example.com"
}
```

---

# Token Introspection

Checks whether an access token is active.

## Request

```http
POST /oidc/introspect
```

### Request Body

```text
token=ACCESS_TOKEN
```

### Example Response

```json
{
  "active": true,
  "sub": "123",
  "scope": "openid profile email"
}
```

---

# JSON Web Key Set (JWKS)

Returns the public keys used to validate JWT signatures.

## Request

```http
GET /.well-known/jwks.json
```

---

# Supported Scopes

| Scope | Description |
|---------|-------------|
| openid | OpenID Connect Authentication |
| profile | User Profile |
| email | User Email Address |

---

# Supported Claims

| Claim | Description |
|-------|-------------|
| sub | Subject Identifier |
| uid | Username |
| user_id | Internal User ID |
| db | Odoo Database |
| name | Full Name |
| email | Email Address |

---

# Supported Response Types

- code
- token
- id_token

---

# Supported Client Authentication

- client_secret_post
- client_secret_basic

---

# Supported ID Token Signing Algorithm

```
HS512
```

---

# Authentication Flow

```text
+-----------+                                  +----------------+
|  Client   |                                  | OIDC Provider  |
+-----+-----+                                  +-------+--------+
      |                                                |
      | GET /oidc/authorize                            |
      |----------------------------------------------->|
      |                                                |
      |<------ Login & User Consent -------------------|
      |                                                |
      | Authorization Code                             |
      |<-----------------------------------------------|
      |                                                |
      | POST /oidc/token                               |
      |----------------------------------------------->|
      |                                                |
      | Access Token + ID Token                        |
      |<-----------------------------------------------|
      |                                                |
      | GET /oidc/userinfo                             |
      | Authorization: Bearer ACCESS_TOKEN             |
      |----------------------------------------------->|
      |                                                |
      | User Information                               |
      |<-----------------------------------------------|
```

---

# Error Response

Example:

```json
{
  "error": "invalid_grant",
  "error_description": "Authorization code has expired."
}
```

Common error codes:

| Error | Description |
|--------|-------------|
| invalid_request | Missing or invalid request parameter |
| invalid_client | Invalid client credentials |
| invalid_grant | Invalid or expired authorization code |
| unauthorized_client | Client not authorized for the requested grant |
| unsupported_grant_type | Unsupported grant type |
| invalid_scope | Invalid or unsupported scope |
| access_denied | User denied the request |
| server_error | Internal server error |
| temporarily_unavailable | Service temporarily unavailable |

---

# Security Recommendations

- Always use **HTTPS** for all OAuth2/OIDC endpoints.
- Validate the `state` parameter to prevent CSRF attacks.
- Use a cryptographically secure `nonce` when requesting ID Tokens.
- Store Access Tokens securely and avoid exposing them in URLs.
- Verify the ID Token signature using the JWKS endpoint.
- Validate the issuer (`iss`) and audience (`aud`) claims before accepting an ID Token.

---

# Standards

This implementation follows the following specifications:

- OAuth 2.0 (RFC 6749)
- OAuth 2.0 Token Introspection (RFC 7662)
- OpenID Connect Core 1.0
- OpenID Connect Discovery 1.0
- JSON Web Token (JWT)
- JSON Web Key (JWK)