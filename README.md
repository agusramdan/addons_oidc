# OIDC Provider and Authentication for Odoo

OpenID Connect (OIDC) Provider and Authentication module for Odoo.

This module extends OAuth authentication and provides complete OpenID Connect (OIDC) support for both:

- OIDC Authentication Client
- OIDC Identity Provider (IdP)

Using this module, Odoo can act as:

- OpenID Connect Client
- OpenID Connect Identity Provider
- Single Sign-On (SSO) Server

---

# Features

# OIDC Authentication Client

Authenticate users using external OpenID Connect providers:

- Keycloak
- Authentik
- Azure AD
- Google
- Okta
- Auth0
- GitLab
- Custom OIDC Provider

Supports:

- Authorization Code Flow
- OpenID Discovery
- Access Token
- ID Token
- UserInfo Endpoint
- JWT Validation

---

# OIDC Provider (Identity Provider)

Odoo can act as OpenID Connect Identity Provider.

Supports endpoints:

- Authorization Endpoint
- Token Endpoint
- UserInfo Endpoint
- JWKS Endpoint
- OpenID Configuration Endpoint
- Logout Endpoint

---

# Single Sign-On (SSO)

Provides centralized authentication for:

- Internal Applications
- Portal
- Third Party Applications
- External Services

---

# Automatic OpenID Discovery

Supports:

```text
/.well-known/openid-configuration
```

Automatically publishes:

- issuer
- authorization_endpoint
- token_endpoint
- userinfo_endpoint
- jwks_uri
- end_session_endpoint

---

# JWT Support

Supports:

- JWT Access Token
- JWT ID Token
- RS256 Signing
- JWKS Key Publishing

---

# User Synchronization

Supports automatic:

- User Creation
- User Update
- Email Mapping
- Group Mapping
- Role Synchronization

---

# Multi Provider Support

Supports multiple external identity providers simultaneously.

Examples:

- Google Login
- Internal SSO
- Azure Login
- Partner Identity

---

# Module Structure

```text
amr_oidc/
├── controllers/
├── models/
├── security/
├── views/
├── data/
├── static/
├── wizard/
├── README.md
└── __manifest__.py
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/agusramdan/addons_oidc.git
```

---

## Addons Path

Add module path into Odoo configuration:

```ini
addons_path = addons,custom_addons
```

---

## Install Dependencies

```bash
pip install requests pyjwt cryptography
```

---

## Restart Odoo

```bash
sudo systemctl restart odoo
```

---

## Update Apps List

Navigate to:

```text
Apps → Update Apps List
```

Install:

```text
OIDC Provider and Authentication
```

---

# Configuration

# Configure External OIDC Provider

Navigate to:

```text
Settings → Authentication → OAuth Providers
```

Create new provider.

---

## Example Keycloak Provider

### Discovery URL

```text
https://keycloak.example.com/realms/master/.well-known/openid-configuration
```

### Client ID

```text
odoo-client
```

### Redirect URI

```text
https://odoo.example.com/auth_oauth/signin
```

---

# Configure Odoo as OIDC Provider

Navigate to:

```text
Settings → Authentication → OIDC Provider
```

Configure:

- Issuer URL
- Signing Key
- Client Applications
- Redirect URIs
- Scopes

---

# Available Endpoints

## OpenID Configuration

```text
/.well-known/openid-configuration
```

---

## Authorization Endpoint

```text
/oidc/authorize
```

---

## Token Endpoint

```text
/oidc/token
```

---

## UserInfo Endpoint

```text
/oidc/userinfo
```

---

## JWKS Endpoint

```text
/oidc/jwks
```

---

## Logout Endpoint

```text
/oidc/logout
```

---

# Example OpenID Configuration

```json
{
  "issuer": "https://odoo.example.com",
  "authorization_endpoint": "https://odoo.example.com/oidc/authorize",
  "token_endpoint": "https://odoo.example.com/oidc/token",
  "userinfo_endpoint": "https://odoo.example.com/oidc/userinfo",
  "jwks_uri": "https://odoo.example.com/oidc/jwks"
}
```

---

# Supported Claims

| Claim | Description |
|---|---|
| sub | User unique identifier |
| email | User email |
| preferred_username | Username |
| given_name | First name |
| family_name | Last name |
| groups | User groups |

---

# Group Mapping

Supports mapping OIDC groups into Odoo groups.

| OIDC Group | Odoo Group |
|---|---|
| admin | Administration |
| hr | HR User |
| finance | Accounting User |

---

# Security

Supports:

- JWT Signature Validation
- Nonce Validation
- Expiration Validation
- Audience Validation
- HTTPS Enforcement
- RS256 Signing

---

# Authentication Flow

```text
User
  ↓
Odoo Client
  ↓
OIDC Provider
  ↓
Authorization Code
  ↓
Access Token
  ↓
ID Token
  ↓
Authenticated Session
```

---

# Odoo as Identity Provider Flow

```text
Application
  ↓
Odoo OIDC Provider
  ↓
User Authentication
  ↓
Authorization Code
  ↓
Token Exchange
  ↓
Access Token / ID Token
```

---

# Supported Odoo Versions

- Odoo 13
- Odoo 14
- Odoo 15
- Odoo 16
- Odoo 17

---

# Technical Features

- OAuth2 Support
- OpenID Connect Support
- JWT Token Generation
- JWKS Key Publishing
- Multi Provider Authentication
- Dynamic Discovery
- Generic OIDC Architecture

---

# Development

## Run Odoo

```bash
python odoo-bin -d test_db -u amr_oidc
```

---

# License

LGPL-3

---

# Author

Your Company Name

---

# Contribution

Contributions and pull requests are welcome.
