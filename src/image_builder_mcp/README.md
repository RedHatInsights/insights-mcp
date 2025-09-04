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

For example questions specific to each toolset please have a look at the test files:

 * [`image-builder-mcp`](tests/test_llm_integration_easy.py#L20)
 * [`image-builder-mcp`](tests/test_llm_integration_hard.py#L16)

### Custom Repository Tests
The test suite includes specific tests for custom repository handling:
- **Test**: `test_custom_repositories_guidance` in `tests/test_llm_integration_easy.py`
- **Prompt**: "I want to create a RHEL 9 image with custom repositories. Can you help me set that up?"
- **Expected**: LLM should guide user to use `content-sources_mcp` and explain dual inclusion requirement

- **Test**: `test_epel_repository_lookup` in `tests/test_llm_integration_easy.py`
- **Prompt**: "I want to add EPEL repository to my RHEL 9 image. Can you help me find the correct repository UUID?"
- **Expected**: LLM should call content-sources_list_repositories and provide actual UUIDs, not fake ones
