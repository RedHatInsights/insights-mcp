# Image Builder MCP

This is the Image Builder MCP.

## Important Notes

### Custom Repositories
When adding custom repositories to blueprints, you **MUST** include them in both:
- `payload_repositories` - for package installation during build
- `custom_repositories` - for repository configuration in the final image

This dual inclusion is required for the blueprint to work correctly. Use the `content-sources_mcp` tool to find repository UUIDs.

## Customizations

All customizations are documented in the [blueprint reference](https://osbuild.org/docs/user-guide/blueprint-reference/).

The following table shows if the customization was tested once manually and if an automatic test was added.

| Customization | Manual Test | Automatic Test |
|---------------|-------------|----------------|
| `distro` | ✅ | ❌ |
| `packages` | ✅ | ❌ |
| `groups` | ✅ | ❌ |
| `containers` | ❌ | ❌ |
| `customizations.hostname` | ✅ | ❌ |
| `customizations.kernel` | ✅ | ❌ |
| `customizations.subscription` | ✅ | ❌ |
| `customizations.rpm` | ❌ | ❌ |
| `customizations.sshkey` | ❌ | ❌ |
| `customizations.user` | ✅ | ❌ |
| `customizations.group` | ✅ | ❌ |
| `customizations.timezone` | ✅ | ❌ |
| `customizations.locale` | ✅ | ❌ |
| `customizations.firewall` | ✅ | ❌ |
| `customizations.services` | ✅ | ❌ |
| `customizations.files` | ❌ | ❌ |
| `customizations.directories` | ❌ | ❌ |
| `customizations.installation_device` | ❌ | ❌ |
| `customizations.ignition` | ❌ | ❌ |
| `customizations.fdo` | ❌ | ❌ |
| `customizations.repos` | ❌ | ❌ |
| `customizations.partitioning` | ❌ | ❌ |
| `customizations.filesystem` | ❌ | ❌ |
| `customizations.disk` | ❌ | ❌ |
| `customizations.openscap` | ❌ | ❌ |
| `customizations.openscap.tailoring` | ❌ | ❌ |
| `customizations.fips` | ❌ | ❌ |
| `customizations.installer` | ❌ | ❌ |
| `customizations.installer.kickstart` | ❌ | ❌ |
| `customizations.installer.modules` | ❌ | ❌ |
| **Image Types** | | |
| `image_type: guest-image` | ✅ | ❌ |
| `image_type: ami` | ❌ | ❌ |
| `image_type: aws` (legacy) | ❌ | ❌ |
| `image_type: azure` | ❌ | ❌ |
| `image_type: edge-commit` | ❌ | ❌ |
| `image_type: edge-installer` | ❌ | ❌ |
| `image_type: gcp` | ❌ | ❌ |
| `image_type: image-installer` | ❌ | ❌ |
| `image_type: oci` | ✅ | ❌ |
| `image_type: rhel-edge-commit` | ❌ | ❌ |
| `image_type: vhd` | ❌ | ❌ |
| `image_type: vsphere` | ❌ | ❌ |
| `image_type: vsphere-ova` | ❌ | ❌ |
| `image_type: wsl` | ❌ | ❌ |
| **Upload Targets** | | |
| `upload_target: aws` | ❌ | ❌ |
| `upload_target: aws.s3` | ✅ | ❌ |
| `upload_target: azure` | ❌ | ❌ |
| `upload_target: gcp` | ❌ | ❌ |
| `upload_target: oci.objectstorage` | ✅ | ❌ |


## Test Prompts

For example questions, see the generated [Image Builder test prompts](test_prompts.md).
The generated LLM test suite is implemented in
[`tests/test_image_builder_llm_prompts.py`](tests/test_image_builder_llm_prompts.py).
Run it with `uv run pytest -m llm -k image_builder` after configuring `test_config.json` and Insights
credentials. See [`tests/README.md`](../../tests/README.md) for the shared LLM test setup.
