from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dscg.model_config import (
    DASHSCOPE_NON_THINKING_MODEL_IDS,
    DASHSCOPE_STRICT_SCHEMA_MODEL_IDS,
    DEEPSEEK_MODEL_IDS,
    PROVIDER_PRESETS,
    load_model_settings,
    reasoning_effort_for_config,
    resolve_model_config,
    thinking_request_options,
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

    def test_deepseek_thinking_is_disabled_for_agentdojo_compatibility(self):
        config = resolve_model_config(
            local_settings={
                "main": {
                    "provider": "deepseek",
                    "model_id": "deepseek-flash",
                    "api_key": "test-key",
                }
            },
            env={},
        )

        self.assertEqual(reasoning_effort_for_config(config), "none")

    def test_thinking_default_models_get_explicit_non_thinking_switch(self):
        self.assertEqual(DASHSCOPE_NON_THINKING_MODEL_IDS,
                         ("qwen3.5-flash", "qwen3.7-plus", "qwen3.8-flash"))
        for model_id in DASHSCOPE_NON_THINKING_MODEL_IDS:
            with self.subTest(model_id=model_id):
                self.assertIn(model_id, DASHSCOPE_STRICT_SCHEMA_MODEL_IDS)
                config = resolve_model_config(
                    local_settings={"main": {"provider": "dashscope",
                                              "model_id": model_id, "api_key": "test-key"}},
                    env={},
                )
                self.assertEqual(thinking_request_options(config),
                                 {"extra_body": {"enable_thinking": False}})
                self.assertIs(config.public_dict()["enable_thinking"], False)
                self.assertIsNone(reasoning_effort_for_config(config))
                dated = resolve_model_config(
                    local_settings={"main": {"provider": "dashscope",
                                              "model_id": model_id + "-2026-01-01",
                                              "api_key": "test-key"}},
                    env={},
                )
                self.assertEqual(thinking_request_options(dated),
                                 {"extra_body": {"enable_thinking": False}})

    def test_recorded_and_out_of_scope_models_keep_existing_request_bytes(self):
        recorded = resolve_model_config(
            local_settings={"main": {"provider": "dashscope",
                                      "model_id": "qwen3.7-flash", "api_key": "test-key"}},
            env={},
        )
        self.assertEqual(thinking_request_options(recorded), {})
        self.assertNotIn("enable_thinking", recorded.public_dict())
        self.assertEqual(reasoning_effort_for_config(recorded), "none")
        outside = resolve_model_config(
            local_settings={"main": {"provider": "dashscope",
                                      "model_id": "qwen3.8-max", "api_key": "test-key"}},
            env={},
        )
        self.assertEqual(thinking_request_options(outside), {})
        self.assertNotIn("enable_thinking", outside.public_dict())


if __name__ == "__main__":
    unittest.main()
