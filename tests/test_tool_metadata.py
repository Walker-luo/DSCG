import tempfile
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch
import dscg.tool_metadata as tool_metadata
import experiments.tools.generate_tool_metadata as metadata_generator

from agentdojo.functions_runtime import FunctionsRuntime

from dscg.tool_metadata import (
    ToolMetadataError,
    ToolRiskMetadata,
    load_tool_metadata,
    metadata_for_runtime,
    set_tool_metadata,
)
from experiments.tools.generate_tool_metadata import generate, registered_tools, validate_catalog


class ToolMetadataTests(unittest.TestCase):
    def test_schema_classifies_risk_and_confirmation(self):
        metadata = ToolRiskMetadata(
            effect="external_send",
            source="email",
            sink="external_recipient",
            sensitivity="personal",
            idempotent=False,
            reversible=False,
        )
        self.assertEqual(metadata.risk_level, "critical")
        self.assertTrue(metadata.confirmation_required)
        self.assertTrue(metadata.audit_required)

    def test_sink_prevents_public_read_fast_path(self):
        metadata = ToolRiskMetadata(
            effect="read",
            source="web",
            sink="public_output",
            sensitivity="public",
            idempotent=True,
            reversible=True,
        )
        self.assertEqual(metadata.risk_level, "high")
        self.assertFalse(metadata.deterministic_read)
        self.assertTrue(metadata.audit_required)

    def test_invalid_cross_field_metadata_is_rejected(self):
        with self.assertRaises(ToolMetadataError):
            ToolRiskMetadata(
                effect="external_send",
                source="email",
                sink="none",
                sensitivity="public",
                idempotent=True,
                reversible=True,
            )

    def test_catalog_must_reference_registered_tools(self):
        runtime = FunctionsRuntime()
        with self.assertRaises(ToolMetadataError):
            set_tool_metadata(runtime, {"missing_tool": {
                "effect": "read",
                "source": "local",
                "sink": "none",
                "sensitivity": "public",
                "idempotent": True,
                "reversible": True,
            }})

    def test_toml_loader_reads_tools_table(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tools.toml"
            path.write_text(
                "[tools.lookup]\n"
                "effect = 'read'\n"
                "source = 'local'\n"
                "sink = 'none'\n"
                "sensitivity = 'public'\n"
                "idempotent = true\n"
                "reversible = true\n",
                encoding="utf-8",
            )
            catalog = load_tool_metadata(path)
        self.assertEqual(catalog["lookup"]["effect"], "read")

    def test_explicit_missing_catalog_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ToolMetadataError, "does not exist"):
                load_tool_metadata(Path(directory) / "missing.toml")

    def test_generated_catalog_covers_all_active_backend_suites(self):
        suites = registered_tools()
        expected = set().union(*suites.values())
        self.assertEqual(set(validate_catalog(suites=suites)), expected)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "tools.toml"
            generate(output)
            self.assertEqual(set(load_tool_metadata(output)), expected)
            with self.assertRaisesRegex(ToolMetadataError, "already exists"):
                generate(output)

    def test_catalog_rejects_missing_classification(self):
        suites = registered_tools()
        first = next(iter(suites))
        suites[first] = suites[first] | {"unclassified_tool"}
        with self.assertRaisesRegex(ToolMetadataError, "unclassified_tool"):
            validate_catalog(suites=suites)

    def test_generator_rejects_unpinned_backend_as_metadata_configuration_error(self):
        from dscg.benchmark_catalog import BenchmarkConfigurationError
        with patch("dscg.benchmark_catalog.get_backend", side_effect=BenchmarkConfigurationError("wrong revision")):
            with self.assertRaisesRegex(ToolMetadataError, "wrong revision"):
                registered_tools()

    def test_benchmark_coverage_rejects_legacy_override_before_runtime(self):
        validator = getattr(tool_metadata, "validate_benchmark_tool_metadata", None)
        self.assertTrue(callable(validator), "benchmark coverage validator is required")
        with self.assertRaisesRegex(ToolMetadataError, "browse_webpage"):
            validator("config/tools.agentdojo-v1.2.toml", required_tools={"browse_webpage"})

    def test_benchmark_validation_keeps_override_precedence_and_checks_schema(self):
        validator = getattr(tool_metadata, "validate_benchmark_tool_metadata", None)
        self.assertTrue(callable(validator), "benchmark coverage validator is required")
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "local.toml"
            local.write_text('[tools.browse_webpage]\neffect="read"\n')
            with patch.object(tool_metadata, "DEFAULT_TOOL_METADATA_PATH", local):
                with self.assertRaisesRegex(ToolMetadataError, "browse_webpage"):
                    validator(local, required_tools={"browse_webpage"}, env={})
                validated = validator("config/tools.agentdyn-v1.2.toml", required_tools={"browse_webpage"}, env={})
            self.assertEqual(validated["browse_webpage"].risk_level, "critical")

    def test_benchmark_validation_rejects_non_scalar_metadata_with_tool_context(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.toml"
            invalid.write_text(
                '[tools.browse_webpage]\neffect=["read"]\nsource="web"\n'
                'sink="none"\nsensitivity="public"\nidempotent=true\nreversible=true\n'
            )
            with self.assertRaisesRegex(ToolMetadataError, "browse_webpage"):
                tool_metadata.validate_benchmark_tool_metadata(invalid, required_tools={"browse_webpage"})

    def test_dynamic_handlers_and_deferred_verification_never_use_read_bypass(self):
        catalog = load_tool_metadata("config/tools.agentdyn-v1.2.toml")
        for name in ("browse_webpage", "input_to_webpage", "verify_transaction", "verify_shopping_account", "verify_github_account"):
            with self.subTest(tool=name):
                metadata = ToolRiskMetadata(**catalog[name])
                self.assertEqual(metadata.risk_level, "critical")
                self.assertNotEqual(metadata.effect, "read")
                self.assertFalse(metadata.idempotent)
                self.assertFalse(metadata.deterministic_read)
                self.assertTrue(metadata.audit_required)


    def test_downloads_unread_mail_and_invoice_are_effectful(self):
        catalog = load_tool_metadata("config/tools.agentdyn-v1.2.toml")
        for name in ("download_file_through_id", "download_file_through_url", "get_unread_emails", "get_shopping_linked_unread_emails", "get_github_linked_unread_emails", "get_invoice", "git_get_linked_ssh_keys"):
            with self.subTest(tool=name):
                metadata = ToolRiskMetadata(**catalog[name])
                self.assertNotEqual(metadata.effect, "read")
                self.assertFalse(metadata.deterministic_read)
                self.assertTrue(metadata.audit_required)

    def test_missing_metadata_is_explicitly_critical(self):
        runtime = FunctionsRuntime()

        @runtime.register_function
        def read_profile() -> str:
            """Read a profile."""
            return "profile"

        status = metadata_for_runtime(runtime)["read_profile"]
        self.assertFalse(status.registered)
        self.assertEqual(status.risk_level, "critical")
        self.assertEqual(status.error_code, "METADATA_MISSING")


class DualBackendMetadataTests(unittest.TestCase):
    @contextmanager
    def selection_paths(self, active):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profiles = {}
            for name in ("agentdojo", "agentdyn"):
                source = Path("config") / f"tools.{name}-v1.2.toml"
                target = root / source
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
                profiles[name] = SimpleNamespace(id=name, label=name, tool_metadata_path=target,
                    suites=("workspace", "travel", "banking", "slack") if name=="agentdojo" else ("shopping", "github", "dailylife"), suite_version="v1.2")
            with patch.object(tool_metadata, "PROJECT_ROOT", root), patch.object(tool_metadata, "DEFAULT_TOOL_METADATA_PATH", root/"config/tools.local.toml"), patch("dscg.benchmark_catalog.get_backend", return_value=profiles[active]):
                yield root, profiles

    def test_copy_of_other_backend_generic_is_skipped_with_visible_reason(self):
        with self.selection_paths("agentdyn") as (root, profiles):
            generic=root/"config/tools.local.toml"
            generic.write_bytes(profiles["agentdojo"].tool_metadata_path.read_bytes())
            before=generic.read_bytes()
            with self.assertWarnsRegex(UserWarning, "agentdojo"):
                metadata=load_tool_metadata(env={})
            self.assertIn("browse_webpage", metadata)
            self.assertNotIn("get_webpage", metadata)
            selected=tool_metadata.resolve_tool_metadata(env={}).public_dict()
            self.assertEqual(selected["backend_id"], "agentdyn")
            self.assertEqual(selected["catalog_backend_id"], "agentdyn")
            self.assertEqual(selected["source"], "builtin")
            self.assertEqual(selected["skipped_generic_path"], str(generic))
            self.assertIn("agentdojo", selected["warning"])
            self.assertEqual(generic.read_bytes(), before)

    def test_semantically_equal_own_generic_wins_despite_comments_and_order(self):
        with self.selection_paths("agentdojo") as (root, profiles):
            generic=root/"config/tools.local.toml"
            entries=[line for line in profiles["agentdojo"].tool_metadata_path.read_text().splitlines() if line and not line.startswith("#") and "=" in line]
            generic.write_text("# local copy with reversed entry order\n[tools]\n"+"\n".join(reversed(entries))+"\n")
            selected=tool_metadata.resolve_tool_metadata(env={})
            self.assertEqual(selected.source, "generic_local")
            self.assertEqual(selected.catalog_backend_id, "agentdojo")
            self.assertIn("get_webpage", load_tool_metadata(env={}))

    def test_modified_reviewed_copy_is_custom_instead_of_silently_skipped(self):
        with self.selection_paths("agentdyn") as (root, profiles):
            generic=root/"config/tools.local.toml"
            lines=profiles["agentdojo"].tool_metadata_path.read_text().splitlines()
            lines=[line.replace('sensitivity = "public"','sensitivity = "personal"') if line.startswith("get_webpage =") else line for line in lines]
            generic.write_text("\n".join(lines)+"\n")
            self.assertEqual(load_tool_metadata(generic)["get_webpage"]["sensitivity"],"personal")
            with self.assertRaisesRegex(ToolMetadataError,"unassigned custom"):
                load_tool_metadata(env={})

    def test_recognized_agentdyn_copy_is_skipped_when_agentdojo_is_active(self):
        with self.selection_paths("agentdojo") as (root, profiles):
            generic=root/"config/tools.local.toml"
            generic.write_bytes(profiles["agentdyn"].tool_metadata_path.read_bytes())
            with self.assertWarnsRegex(UserWarning,"agentdyn"):
                metadata=load_tool_metadata(env={})
            self.assertIn("get_webpage",metadata)
            self.assertNotIn("browse_webpage",metadata)

    def test_unassigned_generic_custom_catalog_fails_closed_without_explicit_choice(self):
        with self.selection_paths("agentdyn") as (root, profiles):
            generic=root/"config/tools.local.toml"
            generic.write_text('[tools.custom]\neffect="read"\n')
            with self.assertRaisesRegex(ToolMetadataError, "unassigned|custom|ambiguous"):
                load_tool_metadata(env={})
            self.assertEqual(set(load_tool_metadata(generic,env={})), {"custom"})
            selected=tool_metadata.resolve_tool_metadata(generic,env={},backend=profiles["agentdyn"])
            self.assertEqual(selected.public_dict()["backend_id"], "agentdyn")
            self.assertEqual(selected.source, "explicit")

    def test_backend_local_precedes_ambiguous_generic_and_explicit_precedes_env(self):
        with self.selection_paths("agentdyn") as (root, profiles):
            generic=root/"config/tools.local.toml"
            generic.write_text('[tools.ambiguous]\neffect="read"\n')
            local=root/"config/tools.agentdyn.local.toml"
            local.write_text('[tools.local]\neffect="write"\n')
            override=root/"override.toml"
            override.write_text('[tools.override]\neffect="delete"\n')
            self.assertEqual(set(load_tool_metadata(env={})), {"local"})
            env={"DSCG_TOOL_METADATA":str(override)}
            self.assertEqual(set(load_tool_metadata(env=env)), {"override"})
            self.assertEqual(set(load_tool_metadata(local,env=env)), {"local"})

    def test_generator_defaults_are_backend_specific_and_generic_is_protected(self):
        for active in ("agentdojo", "agentdyn"):
            with self.subTest(backend=active), self.selection_paths(active) as (root, profiles):
                profile=profiles[active]
                generic=root/"config/tools.local.toml"
                generic.write_text("# preserve user file\n")
                names=set(load_tool_metadata(profile.tool_metadata_path))
                with patch.object(metadata_generator, "PROJECT_ROOT", root), patch.object(metadata_generator, "registered_tools", return_value={"fixture":names}):
                    output=generate()
                    self.assertEqual(output,root/f"config/tools.{active}.local.toml")
                    self.assertEqual(output.read_bytes(),profile.tool_metadata_path.read_bytes())
                    with self.assertRaisesRegex(ToolMetadataError,"generic|backend-specific"):
                        generate(generic,force=True)
                self.assertEqual(generic.read_text(),"# preserve user file\n")



if __name__ == "__main__":
    unittest.main()
