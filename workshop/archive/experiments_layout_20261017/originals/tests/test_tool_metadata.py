import tempfile
import unittest
from pathlib import Path

from agentdojo.functions_runtime import FunctionsRuntime

from dscg.tool_metadata import (
    ToolMetadataError,
    ToolRiskMetadata,
    load_tool_metadata,
    metadata_for_runtime,
    set_tool_metadata,
)
from experiments.generate_tool_metadata import generate, registered_tools, validate_catalog


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

    def test_generated_catalog_covers_all_agentdojo_suites(self):
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
        suites["workspace"] = suites["workspace"] | {"unclassified_tool"}
        with self.assertRaisesRegex(ToolMetadataError, "unclassified_tool"):
            validate_catalog(suites=suites)

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


if __name__ == "__main__":
    unittest.main()
