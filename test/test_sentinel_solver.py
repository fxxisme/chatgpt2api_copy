from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("CHATGPT2API_AUTH_KEY", "test-auth")

from services import openai_backend_api as backend_module
from services import sentinel_solver_client as client_module
from services.config import config
from services.openai_backend_api import DEFAULT_IMPERSONATE, ChatRequirements, OpenAIBackendAPI


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: object = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = str(self._payload)

    def json(self) -> object:
        return self._payload


def solver_config(url: str = "http://solver:8080", key: str = "solver-key"):
    return mock.patch.multiple(
        type(config),
        sentinel_solver_url=mock.PropertyMock(return_value=url),
        sentinel_solver_key=mock.PropertyMock(return_value=key),
    )


class SentinelSolverClientTests(unittest.TestCase):
    def setUp(self) -> None:
        client_module._user_agent_cache.update(url="", value="", expires_at=0.0)

    def test_solve_turnstile_calls_solver_with_key(self) -> None:
        with solver_config(), mock.patch.object(
            client_module.requests, "post", return_value=FakeResponse(200, {"token": "solved"})
        ) as post:
            self.assertEqual(client_module.solve_turnstile("dx-value", "p-value"), "solved")

        args, kwargs = post.call_args
        self.assertEqual(args[0], "http://solver:8080/v1/turnstile")
        self.assertEqual(kwargs["json"], {"dx": "dx-value", "p": "p-value"})
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer solver-key")

    def test_solve_turnstile_falls_back_to_local_solver_when_solver_fails(self) -> None:
        with solver_config(), mock.patch.object(
            client_module.requests, "post", side_effect=RuntimeError("connection refused")
        ), mock.patch.object(client_module, "solve_turnstile_token", return_value="local") as local:
            self.assertEqual(client_module.solve_turnstile("dx", "p"), "local")
        local.assert_called_once_with("dx", "p")

    def test_solve_turnstile_without_solver_uses_local_solver(self) -> None:
        with solver_config(url=""), mock.patch.object(client_module.requests, "post") as post, mock.patch.object(
            client_module, "solve_turnstile_token", return_value=None
        ):
            self.assertEqual(client_module.solve_turnstile("dx", "p"), "")
        post.assert_not_called()

    def test_solver_user_agent_is_cached(self) -> None:
        with solver_config(), mock.patch.object(
            client_module.requests, "get", return_value=FakeResponse(200, {"user_agent": "SolverUA/1.0"})
        ) as get:
            self.assertEqual(client_module.solver_user_agent(), "SolverUA/1.0")
            self.assertEqual(client_module.solver_user_agent(), "SolverUA/1.0")
        get.assert_called_once()

    def test_solver_user_agent_empty_without_solver(self) -> None:
        with solver_config(url=""), mock.patch.object(client_module.requests, "get") as get:
            self.assertEqual(client_module.solver_user_agent(), "")
        get.assert_not_called()


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []
        self.headers: dict[str, str] = {}

    def post(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        for suffix, response in self.responses.items():
            if url.endswith(suffix):
                return response
        raise AssertionError(f"unexpected url {url}")


class BackendSentinelTests(unittest.TestCase):
    def test_chat_requirements_finalize_uses_web_fields_and_solver_user_agent(self) -> None:
        api = OpenAIBackendAPI(access_token="token")
        api.session = FakeSession({
            "/prepare": FakeResponse(200, {
                "prepare_token": "prepare-token",
                "proofofwork": {"required": True, "seed": "seed", "difficulty": "0fffff"},
                "turnstile": {"required": True, "dx": "dx-value"},
            }),
            "/finalize": FakeResponse(200, {"token": "requirements-token"}),
        })
        with mock.patch.object(backend_module, "solver_user_agent", return_value="SolverUA/1.0"), mock.patch.object(
            backend_module, "build_legacy_requirements_token", return_value="p-value"
        ) as build_p, mock.patch.object(
            backend_module, "build_proof_token", return_value="proof-value"
        ) as build_proof, mock.patch.object(
            backend_module, "solve_turnstile", return_value="turnstile-value"
        ) as solve:
            requirements = api._get_chat_requirements()

        self.assertEqual(build_p.call_args.args[0], "SolverUA/1.0")
        self.assertEqual(build_proof.call_args.args[2], "SolverUA/1.0")
        solve.assert_called_once_with("dx-value", "p-value")
        finalize_url, finalize_kwargs = api.session.calls[-1]
        self.assertTrue(finalize_url.endswith("/sentinel/chat-requirements/finalize"))
        self.assertEqual(finalize_kwargs["json"], {
            "prepare_token": "prepare-token",
            "proofofwork": "proof-value",
            "turnstile": "turnstile-value",
        })
        self.assertEqual(requirements.token, "requirements-token")
        self.assertEqual(requirements.turnstile_token, "turnstile-value")

    def test_sentinel_user_agent_falls_back_to_request_user_agent(self) -> None:
        api = OpenAIBackendAPI(access_token="token")
        with mock.patch.object(backend_module, "solver_user_agent", return_value=""):
            self.assertEqual(api._sentinel_user_agent(), api.user_agent)

    def test_image_headers_include_turnstile_token(self) -> None:
        api = OpenAIBackendAPI(access_token="token")
        headers = api._image_headers(
            "/backend-api/f/conversation",
            ChatRequirements(token="requirements", proof_token="proof", turnstile_token="turnstile"),
            "conduit",
            "text/event-stream",
        )
        self.assertEqual(headers["OpenAI-Sentinel-Turnstile-Token"], "turnstile")
        self.assertEqual(headers["OpenAI-Sentinel-Proof-Token"], "proof")
        self.assertEqual(headers["X-Conduit-Token"], "conduit")

    def test_legacy_impersonation_is_upgraded(self) -> None:
        with mock.patch.object(backend_module.account_service, "get_account", return_value={"impersonate": "chrome110"}):
            self.assertEqual(OpenAIBackendAPI(access_token="token").fp["impersonate"], DEFAULT_IMPERSONATE)
        with mock.patch.object(backend_module.account_service, "get_account", return_value={"impersonate": "chrome146"}):
            self.assertEqual(OpenAIBackendAPI(access_token="token").fp["impersonate"], DEFAULT_IMPERSONATE)
        with mock.patch.object(backend_module.account_service, "get_account", return_value={"impersonate": "safari17_0"}):
            self.assertEqual(OpenAIBackendAPI(access_token="token").fp["impersonate"], "safari17_0")
        with mock.patch.object(backend_module.account_service, "get_account", return_value={}):
            self.assertEqual(OpenAIBackendAPI(access_token="token").fp["impersonate"], DEFAULT_IMPERSONATE)

    def test_bootstrap_resilient_on_403(self) -> None:
        api = OpenAIBackendAPI(access_token="token")
        mock_resp = mock.Mock()
        mock_resp.status_code = 403
        mock_resp.text = "<html>Cloudflare challenge</html>"
        with mock.patch.object(api.session, "get", return_value=mock_resp):
            api._bootstrap()
            self.assertEqual(api.pow_script_sources, ["https://chatgpt.com/backend-api/sentinel/sdk.js"])


    def test_sentinel_user_agent_syncs_session_headers(self) -> None:
        api = OpenAIBackendAPI(access_token="token")
        with mock.patch.object(backend_module, "solver_user_agent", return_value="Mozilla/5.0 (X11; Linux x86_64)"):
            ua = api._sentinel_user_agent()
            self.assertEqual(ua, "Mozilla/5.0 (X11; Linux x86_64)")
            self.assertEqual(api.session.headers["User-Agent"], "Mozilla/5.0 (X11; Linux x86_64)")
            self.assertEqual(api.session.headers["Sec-Ch-Ua-Platform"], '"Linux"')


class SentinelSolverConfigTests(unittest.TestCase):
    def test_env_overrides_config_and_key_is_hidden(self) -> None:
        env = {"CHATGPT2API_SENTINEL_SOLVER_URL": "http://env-solver:8080/", "CHATGPT2API_SENTINEL_SOLVER_KEY": "env-key"}
        with mock.patch.dict(os.environ, env), mock.patch.dict(
            config.data, {"sentinel_solver_url": "http://file-solver", "sentinel_solver_key": "file-key"}
        ):
            self.assertEqual(config.sentinel_solver_url, "http://env-solver:8080")
            self.assertEqual(config.sentinel_solver_key, "env-key")
            public = config.get()
        self.assertEqual(public["sentinel_solver_url"], "http://env-solver:8080")
        self.assertNotIn("sentinel_solver_key", public)

    def test_timezone_dynamic_offset(self) -> None:
        with mock.patch.dict(os.environ, {"CHATGPT2API_TIMEZONE": "Asia/Tokyo"}):
            self.assertEqual(config.timezone, "Asia/Tokyo")
            self.assertEqual(config.timezone_offset_min, -540)
        with mock.patch.dict(os.environ, {"CHATGPT2API_TIMEZONE": "Asia/Shanghai"}):
            self.assertEqual(config.timezone, "Asia/Shanghai")
            self.assertEqual(config.timezone_offset_min, -480)
        with mock.patch.dict(os.environ, {"CHATGPT2API_TIMEZONE_OFFSET_MIN": "-500"}):
            self.assertEqual(config.timezone_offset_min, -500)


if __name__ == "__main__":
    unittest.main()
