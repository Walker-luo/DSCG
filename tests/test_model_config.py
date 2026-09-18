from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dscg.model_config import (
    DEEPSEEK_MODEL_IDS,
    PROVIDER_PRESETS,
    load_model_settings,
    resolve_model_config,
)


class ModelConfigTests(unittest.TestCase):
    def write_config(self, text: str) -> Path:
        self.tmpdir = TemporaryDirectory()
        path = Path(self.tmpdir.name) / "models.local.toml"
        path.write_text(text, encoding="utf-8")
        self.addCleanup(self.tmpdir.cleanup)
        return path

    def test_loads_local_toml_and_redacts_api_key(self):
        path = self.write_config(
            """
[main]
provider = "deepseek"
model_id = "deepseek-flash"
api_key = "local-main-key"
"""
        )

        settings = load_model_settings(path, env={})
        config = resolve_model_config(config_path=path, env={})

        self.assertEqual(settings["main"]["model_id"], "deepseek-flash")
        self.assertEqual(config.provider, "deepseek")
        self.assertEqual(config.base_url, "https://api.deepseek.com")
        self.assertEqual(config.api_key, "local-main-key")
        self.assertNotIn("api_key", config.public_dict())
        self.assertNotIn("local-main-key", str(config.public_dict()))

    def test_main_and_security_models_can_use_different_providers(self):
        path = self.write_config(
            """
[main]
provider = "deepseek"
model_id = "deepseek-flash"
api_key = "main-key"

[security]
provider = "dashscope"
model_id = "qwen-plus"
api_key = "security-key"
"""
        )

        main_config = resolve_model_config(config_path=path, env={})
        security_config = resolve_model_config(
            prefix="DSCG_SEC",
            config_path=path,
            env={},
            fallback=main_config,
        )

        self.assertEqual(main_config.model_id, "deepseek-flash")
        self.assertEqual(main_config.provider, "deepseek")
        self.assertEqual(security_config.model_id, "qwen-plus")
        self.assertEqual(security_config.provider, "dashscope")
        self.assertEqual(security_config.api_key, "security-key")

    def test_explicit_args_override_env_and_local_config(self):
        path = self.write_config(
            """
[main]
provider = "dashscope"
model_id = "qwen-plus"
api_key = "local-key"
"""
        )
        env = {
            "DSCG_MAIN_PROVIDER": "openai",
            "DSCG_MAIN_MODEL_ID": "env-model",
            "DSCG_MAIN_API_KEY": "env-key",
        }

        config = resolve_model_config(
            model_id="explicit-model",
            provider="deepseek",
            api_key="explicit-key",
            config_path=path,
            env=env,
        )

        self.assertEqual(config.model_id, "explicit-model")
        self.assertEqual(config.provider, "deepseek")
        self.assertEqual(config.api_key, "explicit-key")
        self.assertEqual(config.base_url, "https://api.deepseek.com")

    def test_env_overrides_local_config(self):
        path = self.write_config(
            """
[main]
provider = "dashscope"
model_id = "qwen-plus"
api_key = "local-key"
"""
        )
        env = {
            "DSCG_MAIN_PROVIDER": "deepseek",
            "DSCG_MAIN_MODEL_ID": "env-model",
            "DSCG_MAIN_API_KEY": "env-key",
        }

        config = resolve_model_config(config_path=path, env=env)

        self.assertEqual(config.model_id, "env-model")
        self.assertEqual(config.provider, "deepseek")
        self.assertEqual(config.api_key, "env-key")

    def test_missing_security_config_reuses_primary_config(self):
        main_config = resolve_model_config(
            local_settings={
                "main": {
                    "provider": "custom_gateway",
                    "model_id": "custom-main",
                    "base_url": "https://gateway.example/v1",
                    "api_key": "main-key",
                }
            },
            env={},
        )

        security_config = resolve_model_config(
            prefix="DSCG_SEC",
            local_settings={},
            env={},
            fallback=main_config,
        )

        self.assertEqual(security_config.model_id, main_config.model_id)
        self.assertEqual(security_config.provider, main_config.provider)
        self.assertEqual(security_config.base_url, main_config.base_url)
        self.assertEqual(security_config.api_key, main_config.api_key)

    def test_deepseek_catalog_uses_current_model_ids(self):
        preset = PROVIDER_PRESETS["deepseek"]

        self.assertEqual(DEEPSEEK_MODEL_IDS, ("deepseek-flash", "deepseek-v4-pro"))
        self.assertEqual(preset.base_url, "https://api.deepseek.com")
        self.assertEqual(preset.api_key_env, "DEEPSEEK_API_KEY")


if __name__ == "__main__":
    unittest.main()
