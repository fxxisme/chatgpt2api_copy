import test.utils  # noqa: F401
import unittest
from typing import Any
from fastapi.testclient import TestClient

from api.app import create_app
from services.account_service import AccountService


class MemoryStorage:
    def __init__(self, accounts: list[dict[str, Any]] | None = None) -> None:
        self.accounts = list(accounts or [])

    def load_accounts(self) -> list[dict[str, Any]]:
        return [dict(a) for a in self.accounts]

    def save_accounts(self, accounts: list[dict[str, Any]]) -> None:
        self.accounts = [dict(a) for a in accounts]

    def load_auth_keys(self) -> list[dict[str, Any]]:
        return []

    def save_auth_keys(self, auth_keys: list[dict[str, Any]]) -> None:
        pass

    def health_check(self) -> dict[str, Any]:
        return {"ok": True}

    def get_backend_info(self) -> dict[str, Any]:
        return {"type": "memory"}


class AccountBatchStatusTests(unittest.TestCase):
    def test_batch_update_status_service(self) -> None:
        storage = MemoryStorage(
            [
                {"access_token": "token_1", "status": "正常", "quota": 10},
                {"access_token": "token_2", "status": "正常", "quota": 5},
                {"access_token": "token_3", "status": "异常", "quota": 0},
            ]
        )
        service = AccountService(storage)
        service._image_inflight["token_1"] = 1
        service._image_cooldown_until["token_1"] = 9999999999.0

        # 批量禁用 token_1 和 token_2
        result = service.batch_update_status(["token_1", "token_2", "token_nonexist"], "禁用")
        self.assertEqual(result["updated"], 2)

        # 校验内存中的状态
        tokens_map = {item["access_token"]: item["status"] for item in result["items"]}
        self.assertEqual(tokens_map["token_1"], "禁用")
        self.assertEqual(tokens_map["token_2"], "禁用")
        self.assertEqual(tokens_map["token_3"], "异常")

        # 校验在途与冷却被清理
        self.assertNotIn("token_1", service._image_inflight)
        self.assertNotIn("token_1", service._image_cooldown_until)

        # 校验持久化存储同步
        saved_map = {item["access_token"]: item["status"] for item in storage.accounts}
        self.assertEqual(saved_map["token_1"], "禁用")
        self.assertEqual(saved_map["token_2"], "禁用")

        # 重复调用（幂等性）
        result_idempotent = service.batch_update_status(["token_1", "token_2"], "禁用")
        self.assertEqual(result_idempotent["updated"], 0)

        # 批量重新启用
        result_restore = service.batch_update_status(["token_1", "token_2", "token_3"], "正常")
        self.assertEqual(result_restore["updated"], 3)
        saved_map_restore = {item["access_token"]: item["status"] for item in storage.accounts}
        self.assertEqual(saved_map_restore["token_1"], "正常")
        self.assertEqual(saved_map_restore["token_2"], "正常")
        self.assertEqual(saved_map_restore["token_3"], "正常")

    def test_batch_update_status_api(self) -> None:
        app = create_app()
        client = TestClient(app)

        # 缺少 admin 凭证应当 401
        res = client.post("/api/accounts/batch-status", json={"tokens": ["abc"], "status": "禁用"})
        self.assertEqual(res.status_code, 401)

        from services.config import config
        admin_token = config.auth_key or "test-auth"
        headers = {"Authorization": f"Bearer {admin_token}"}

        # tokens 为空
        res = client.post("/api/accounts/batch-status", json={"tokens": [], "status": "禁用"}, headers=headers)
        self.assertEqual(res.status_code, 400)

        # 无效状态
        res = client.post("/api/accounts/batch-status", json={"tokens": ["abc"], "status": "未知状态"}, headers=headers)
        self.assertEqual(res.status_code, 422)  # Literal validation 错误


if __name__ == "__main__":
    unittest.main()
