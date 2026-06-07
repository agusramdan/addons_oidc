# -*- coding: utf-8 -*-

import base64
import logging
import requests
import time
import uuid
import jwt

from requests.exceptions import (
    ConnectionError,
    Timeout,
    HTTPError,
)

_logger = logging.getLogger(__name__)

SUPPORTED_ALGORITHMS = [
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
]


class AuthenticationProvider:

    def __init__(self, env, credential):
        self.env = env
        self.credential = credential

    def authenticate(self, request_context, audience=None):
        return request_context

    # def get_headers(self, audience=None, ):
    #     raise NotImplementedError()


class ApiKeyProvider(AuthenticationProvider):

    def authenticate(self, request_context, audience=None):
        request_context.setdefault("headers", {})

        request_context["headers"][self.credential["header"]] = self.credential["value"]

        return request_context

    # def get_headers(self, audience=None, ):
    #     return {self.credential["header"]: self.credential["value"]}


class BearerProvider(AuthenticationProvider):

    def authenticate(self, request_context, audience=None):
        request_context.setdefault("headers", {})

        request_context["headers"]["Authorization"] = "Bearer %s" % self.credential["token"]

        return request_context

    # def get_headers(self, audience=None, ):
    #     return {"Authorization": "Bearer %s" % self.credential["token"]}


class BasicProvider(AuthenticationProvider):

    def authenticate(self, request_context, audience=None):
        request_context.setdefault("headers", {})

        token = ("%s:%s" % (self.credential["username"], self.credential["password"],))
        encoded = base64.b64encode(token.encode()).decode()
        request_context["headers"]["Authorization"] = "Basic %s" % encoded

        return request_context

    # def get_headers(self, audience=None, ):
    #     token = ("%s:%s" % (self.credential["username"], self.credential["password"],))
    #     encoded = base64.b64encode(token.encode()).decode()
    #     return {"Authorization": "Basic %s" % encoded}


class ClientSecretProvider(AuthenticationProvider):

    def _get_cache_key(self, audience=None, ):
        return "ClientSecret|%s|%s" % (self.credential["client_id"], audience or "",)

    def _get_token(self, audience=None):
        cache_key = self._get_cache_key(audience or "", )
        token = self.env["service.token.cache"].get_cache(cache_key)
        if token:
            return token

        token_response = self._request_token(audience=audience, )

        self.env["service.token.cache"].set_cache(
            cache_key, token_response["access_token"], token_response["cache_ttl"],
        )

        return token_response["access_token"]

    def _request_token(self, audience=None):

        token_uri = self.credential.get("token_uri")

        if not token_uri:
            raise ValueError("token_uri is required")

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.credential.get("client_id"),
            "client_secret": self.credential.get("client_secret"),
        }

        # Optional Audience
        if audience:
            payload["audience"] = audience

        # Optional Scope
        scope = self.credential.get("scope")

        if scope:

            if isinstance(scope, list):
                payload["scope"] = " ".join(scope)
            else:
                payload["scope"] = scope

        headers = {"Accept": "application/json", }
        connect_timeout = self.credential.get("connect_timeout", 10, )
        read_timeout = self.credential.get("read_timeout", 30, )
        _logger.info("Requesting token ", "client_id=%s ", "audience=%s", self.credential.get("client_id"), audience, )

        try:
            response = requests.post(
                token_uri, headers=headers, data=payload, timeout=(connect_timeout, read_timeout,),
            )

        except Timeout:
            raise ValueError("OIDC token endpoint timeout")
        except ConnectionError:
            raise ValueError("Unable to connect to token endpoint")

        try:
            response.raise_for_status()
        except HTTPError:
            try:
                error_data = response.json()
            except Exception:
                error_data = response.text
            raise ValueError("Token request failed: %s" % error_data)

        try:
            token_response = response.json()
        except Exception:
            raise ValueError("Invalid token response")

        access_token = token_response.get("access_token")

        if not access_token:
            raise ValueError("access_token not found")

        token_type = token_response.get("token_type", "Bearer", )
        expires_in = int(token_response.get("expires_in", 3600, ))
        cache_ttl = max(expires_in - 60, 60, )

        return {
            "access_token": access_token,
            "token_type": token_type,
            "expires_in": expires_in,
            "cache_ttl": cache_ttl,
            "raw_response": token_response,
        }

    def authenticate(self, request_context, audience=None):
        request_context.setdefault("headers", {})

        request_context["headers"]["Authorization"] = "Bearer %s" % self._get_token(audience=audience)

        return request_context

    # def get_headers(self, audience=None, ):
    #     return {"Authorization": "Bearer %s" % self._get_token(audience=audience)}


class ServiceAccountProvider(ClientSecretProvider):

    def _load_private_key(self):

        private_key = self.credential.get("private_key")

        if private_key:
            return private_key

        private_key_file = self.credential.get("private_key_file")

        if not private_key_file:
            raise ValueError(
                "Missing private key"
            )

        with open(private_key_file, "r", encoding="utf-8", ) as fp:
            return fp.read()

    def _get_cache_key(self, audience=None, ):
        return "ServiceAccount|%s|%s" % (self.credential["client_id"], audience or "",)

    def _request_token(self, audience=None):
        """
        Request access token using JWT Bearer Assertion.

        RFC 7523:
        grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
        """

        token_uri = self.credential.get("token_uri")

        if not token_uri:
            raise ValueError("token_uri is required")

        assertion = self._create_jwt_assertion(audience=audience, )

        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }

        # Optional Audience
        if audience:
            payload["audience"] = audience

        # Optional Scope
        scope = self.credential.get("scope")

        if scope:

            if isinstance(scope, list):
                payload["scope"] = " ".join(scope)
            else:
                payload["scope"] = scope

        headers = {"Accept": "application/json", }
        connect_timeout = self.credential.get("connect_timeout", 10, )
        read_timeout = self.credential.get("read_timeout", 30, )
        _logger.info("Requesting token ", "client_id=%s ", "audience=%s", self.credential.get("client_id"), audience, )

        try:
            response = requests.post(
                token_uri, headers=headers, data=payload, timeout=(connect_timeout, read_timeout,),
            )

        except Timeout:
            raise ValueError("OIDC token endpoint timeout")
        except ConnectionError:
            raise ValueError("Unable to connect to token endpoint")

        try:
            response.raise_for_status()
        except HTTPError:
            try:
                error_data = response.json()
            except Exception:
                error_data = response.text
            raise ValueError("Token request failed: %s" % error_data)

        try:
            token_response = response.json()
        except Exception:
            raise ValueError("Invalid token response")

        access_token = token_response.get("access_token")

        if not access_token:
            raise ValueError("access_token not found")

        token_type = token_response.get("token_type", "Bearer", )
        expires_in = int(token_response.get("expires_in", 3600, ))
        cache_ttl = max(expires_in - 60, 60, )

        return {
            "access_token": access_token,
            "token_type": token_type,
            "expires_in": expires_in,
            "cache_ttl": cache_ttl,
            "raw_response": token_response,
        }

    def _create_jwt_assertion(self, audience=None, ):

        now = int(time.time())
        client_id = self.credential.get("client_id")
        if not client_id:
            raise ValueError("client_id is required")
        token_uri = self.credential.get("token_uri")

        if not token_uri:
            raise ValueError("token_uri is required")

        payload = {
            "iss": client_id,
            "sub": client_id,
            "aud": token_uri,
            "iat": now,
            "exp": now + 300,
            "jti": str(uuid.uuid4()),
        }

        if audience:
            payload["resource"] = audience

        scope = self.credential.get("scope")
        if scope:
            if isinstance(scope, list, ):
                payload["scope"] = " ".join(scope)
            else:
                payload["scope"] = scope

        headers = {}
        private_key_id = self.credential.get("private_key_id")
        if private_key_id:
            headers["kid"] = private_key_id
        private_key = self._load_private_key()
        algorithm = self.credential.get("algorithm", "RS256", )

        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError("Unsupported algorithm")
        return jwt.encode(payload, private_key, algorithm=algorithm, headers=headers, )
