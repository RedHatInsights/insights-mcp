"""Image Builder MCP server for creating and managing Linux images."""

import copy
import json
import logging
import os
from typing import Annotated, Any, Optional

import httpx
from fastmcp.tools import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

from insights_mcp.client import InsightsClient
from insights_mcp.errors import InsightsApiError
from insights_mcp.mcp import InsightsMCP
from tools import OpenAPIReducer

WATERMARK_CREATED = "Blueprint created via insights-mcp"
WATERMARK_UPDATED = "Blueprint updated via insights-mcp"

DEPRECATED_IMAGE_TYPES = frozenset(
    {
        "edge-commit",
        "edge-installer",
        "rhel-edge-commit",
        "rhel-edge-installer",
    }
)


def _filter_deprecated_image_types_from_openapi(spec: dict[str, Any]) -> dict[str, Any]:
    """Remove deprecated image types from the ImageTypes enum in an OpenAPI dict."""
    try:
        enum_values = spec["components"]["schemas"]["ImageTypes"]["enum"]
        if isinstance(enum_values, list):
            spec["components"]["schemas"]["ImageTypes"]["enum"] = [
                value for value in enum_values if value not in DEPRECATED_IMAGE_TYPES
            ]
    except (KeyError, TypeError):
        pass
    return spec


class ImageBuilderMCP(InsightsMCP):
    """MCP server for Red Hat Image Builder integration.

    This server provides tools for creating, managing, and building
    custom Linux images using the Red Hat Image Builder service.
    """

    def __init__(
        self,
        default_response_size: int = 10,
    ):
        self.default_response_size = default_response_size
        # TBD: make this configurable
        # probably we want to destiguish a hosted MCP server from
        # a local one (deployed by a customer)
        self.image_builder_mcp_client_id = "mcp"

        self.logger = logging.getLogger("ImageBuilderMCP")

        general_intro = """Image Builder assistant. Use tool_calls, not code samples.
        Compose = one image build job (status: pending, running, success, failure); not a blueprint.
        Image build status, latest build, recent builds → get_composes first; get_compose_details if UUID known.
        🟢 list/status: get_blueprints, get_composes, get_*_details, get_openapi, get_distributions.
        🔴 create_blueprint: gather fields first. 🟡 blueprint_compose: need UUID.
        Paging: follow [PAGE] in list tool responses."""

        super().__init__(
            name="Image Builder MCP Server",
            toolset_name="image-builder",
            api_path="api/image-builder/v1",
            headers={"X-ImageBuilder-ui": self.image_builder_mcp_client_id},
            instructions=general_intro,
        )

        # cache the client for all users
        # TBD: purge cache after some time
        self.clients = {self.insights_client.client_id: self.insights_client}

    def _list_response_paging_instructions(
        self,
        tool_name: str,
        offset: int,
        returned_count: int,
    ) -> str:
        """Concrete paging rules for the first list-tool response in a conversation."""
        next_offset = offset + returned_count
        return (
            f"[PAGE] Returned {returned_count} row(s) at offset={offset}. "
            f"More data requires another {tool_name} call with offset={next_offset} and the requested "
            f"limit. Do not invent rows, names, or UUIDs.\n"
        )

    def _get_image_types_architectures(self) -> tuple[list[str], list[str]]:
        """Get the list of image types available to build images with."""
        try:
            # TBD: change openapi spec to have a proper schema-enum
            # for image types and architectures
            self.logger.debug("Getting openapi")
            openapi = json.loads(self.get_openapi_synchronous())

            image_types = list(openapi["components"]["schemas"]["ImageTypes"]["enum"])

            # remove deprecated image types - TBD remove or mark as deprecated in the openapi spec
            image_types = [image_type for image_type in image_types if image_type not in DEPRECATED_IMAGE_TYPES]

            image_types.sort()

            architectures = list(openapi["components"]["schemas"]["ImageRequest"]["properties"]["architecture"]["enum"])
            architectures.sort()

            self.logger.debug("Supported image types: %s", image_types)
            self.logger.debug("Supported architectures: %s", architectures)
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise ValueError("Error getting openapi for image types and architectures") from e
        return image_types, architectures

    @staticmethod
    def _compact_tool_description(description_str: str, max_len: int = 96) -> str:
        """First line only, capped — keeps multi-tool gateways within reliable tool-calling limits."""
        first_line = description_str.strip().split("\n", 1)[0].strip()
        if len(first_line) <= max_len:
            return first_line
        return first_line[: max_len - 3] + "..."

    def register_tools(self) -> None:
        """Register all available tools with the MCP server."""
        image_types, architectures = self._get_image_types_architectures()
        if not image_types or not architectures:
            return

        # prepend generic keywords for use of many other tools
        # and register with "self.tool()"
        tool_functions: list[dict[str, Any]] = [
            {"fn": self.get_openapi, "readOnlyHint": True},
            {"fn": self.create_blueprint, "readOnlyHint": False},
            {"fn": self.update_blueprint, "readOnlyHint": False},
            {"fn": self.get_blueprints, "readOnlyHint": True},
            {"fn": self.get_blueprint_details, "readOnlyHint": True},
            {"fn": self.get_composes, "readOnlyHint": True},
            {"fn": self.get_compose_details, "readOnlyHint": True},
            {"fn": self.blueprint_compose, "readOnlyHint": False},
            {"fn": self.get_distributions, "readOnlyHint": True},
            {"fn": self.get_org_id, "readOnlyHint": True},
        ]

        for tool_def in tool_functions:
            f = tool_def["fn"]
            tool = Tool.from_function(f)
            tool.annotations = ToolAnnotations(readOnlyHint=tool_def["readOnlyHint"], openWorldHint=True)
            doc_str = f.__doc__ or ""
            description_str = (
                doc_str.format(
                    architectures=", ".join(architectures),
                    image_types=", ".join(image_types),
                    base_url=self.insights_client.insights_base_url,
                )
                if doc_str
                else ""
            )
            compact = self._compact_tool_description(description_str)
            tool.description = compact
            tool.title = compact
            self.add_tool(tool)

    async def get_distributions(self) -> str:
        """🟢 List RHEL distributions (latest minor per major). No Fedora/CentOS Stream support."""
        try:
            distributions = await self.insights_client.get("distributions")
            return json.dumps(distributions)
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(f"Error getting distributions: {str(e)}") from e

    def get_openapi_synchronous(self) -> str:
        """
        Get OpenAPI spec synchronously to get image types and architectures for tool descriptions.

        This function is synchronous because it is called from the constructor
        before initialization of insights_client.
        """
        base_url = self.insights_client.insights_base_url
        if not base_url:
            raise ValueError("Insights base URL is not set, initialize the client with init_insights_client()")
        api_path = self.api_path
        proxy_url = self.insights_client.proxy_url
        return httpx.get(f"{base_url}/{api_path}/openapi.json", timeout=60, proxy=proxy_url).text

    async def blueprint_compose(
        self, blueprint_uuid: Annotated[str, Field(description="The UUID of the blueprint to compose")]
    ) -> str:
        """🟡 Start compose for a blueprint UUID. Confirm UUID via get_blueprints first."""
        try:
            response = await self.insights_client.post(f"blueprints/{blueprint_uuid}/compose")
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(f"Error: {str(e)} in blueprint_compose {blueprint_uuid}") from e

        if isinstance(response, str):
            return response

        response_str = "[INSTRUCTION] Use the tool get_compose_details to get the details of the compose\n"
        response_str += "like the current build status\n"
        response_str += "[ANSWER] Compose created successfully:"
        build_ids_str: list[str] = []

        if isinstance(response, dict):
            raise InsightsApiError(
                f"Error: the response of blueprint_compose is a dict. This is not expected. "
                f"Response: {json.dumps(response)}"
            )

        for build in response:
            if isinstance(build, dict) and "id" in build:
                build_ids_str.append(f"UUID: {build['id']}")
            else:
                build_ids_str.append(f"Invalid build object: {build}")

        response_str += f"\n{json.dumps(build_ids_str)}"
        response_str += "\nWe could double check the details or start the build/compose"
        return response_str

    async def get_openapi(
        self,
        endpoints: Annotated[
            Optional[str],
            Field(
                None,
                description=(
                    "Comma-separated list of endpoint specs to reduce the spec, e.g. "
                    "'GET:/blueprints,POST:/blueprints'. Only needed for create_blueprint/update_blueprint."
                ),
            ),
        ],
    ) -> str:
        """🟢 OpenAPI spec. Optional endpoints=GET:/blueprints,POST:/blueprints to shrink payload."""
        try:
            response = await self.insights_client.get("openapi.json", noauth=True)
            if endpoints:
                try:
                    endpoint_list = [e.strip() for e in endpoints.split(",") if e.strip()]
                    reducer = OpenAPIReducer.from_response(response)
                    reduced = reducer.reduce(endpoint_list)
                    if isinstance(reduced, dict):
                        reduced = _filter_deprecated_image_types_from_openapi(copy.deepcopy(reduced))
                    return json.dumps(reduced)
                except Exception as reduce_err:  # pylint: disable=broad-exception-caught
                    # Fall back to full spec on any reduction error
                    self.logger.warning("OpenAPI reduction failed: %s", reduce_err)
                    if isinstance(response, dict):
                        response = _filter_deprecated_image_types_from_openapi(copy.deepcopy(response))
                    return json.dumps(response)
            if isinstance(response, dict):
                response = _filter_deprecated_image_types_from_openapi(copy.deepcopy(response))
            return json.dumps(response)
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(str(e)) from e

    async def get_org_id(self) -> str:
        """🟢 RHEL org ID for blueprint registration. Never invent org IDs."""
        try:
            org_id = await self.insights_client.get_org_id()
            if org_id:
                return org_id
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(str(e)) from e
        raise InsightsApiError("Error: No organization ID found")

    async def create_blueprint(
        self,
        data: Annotated[
            dict,
            Field(description="Complete blueprint data formatted according to CreateBlueprintRequest from get_openapi"),
        ],
    ) -> str:
        """🔴 Create blueprint after gathering name, distro, arch, image type, user;
        use get_openapi POST:/blueprints."""
        try:
            if os.environ.get("IMAGE_BUILDER_MCP_DISABLE_DESCRIPTION_WATERMARK", "").lower() != "true":
                desc_parts = [data.get("description", ""), WATERMARK_CREATED]
                data["description"] = "\n".join(filter(None, desc_parts))
            # TBD: programmatically check against openapi
            response = await self.insights_client.post("blueprints", json=data)
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(str(e)) from e

        if isinstance(response, str):
            return response

        if isinstance(response, list):
            raise InsightsApiError(
                "Error: the response of blueprint creation is a list. This is not expected. "
                f"Response: {json.dumps(response)}"
            )

        response_str = "[INSTRUCTION] Use the tool get_blueprint_details to get the details of the blueprint\n"
        response_str += "or ask the user to start the build/compose with blueprint_compose\n"
        response_str += f"Always show a link to the blueprint UI: {self.get_blueprint_url(response['id'])}\n"
        response_str += f"[ANSWER] Blueprint created successfully: {{'UUID': '{response['id']}'}}\n"
        response_str += "We could double check the details or start the build/compose"
        return response_str

    async def update_blueprint(
        self,
        blueprint_uuid: Annotated[str, Field(description="The UUID of the blueprint to update")],
        data: Annotated[
            dict,
            Field(description="Complete blueprint data formatted according to CreateBlueprintRequest from get_openapi"),
        ],
    ) -> str:
        """🟡 Update blueprint. Confirm UUID; schema via get_openapi PUT:/blueprints/{{id}}."""
        try:
            if os.environ.get("IMAGE_BUILDER_MCP_DISABLE_DESCRIPTION_WATERMARK", "").lower() != "true":
                if all(wmark not in data.get("description", "") for wmark in [WATERMARK_CREATED, WATERMARK_UPDATED]):
                    desc_parts = [data.get("description", ""), WATERMARK_UPDATED]
                    data["description"] = "\n".join(filter(None, desc_parts))
            response = await self.insights_client.put(f"blueprints/{blueprint_uuid}", json=data)
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(str(e)) from e

        # Normalize response handling similar to create_blueprint
        if isinstance(response, str):
            return response

        if isinstance(response, list):
            raise InsightsApiError(
                "Error: the response of blueprint update is a list. This is not expected. "
                f"Response: {json.dumps(response)}"
            )

        # Build an instructional answer with a UI link like in create_blueprint
        instruction = (
            "[INSTRUCTION] Use the tool get_blueprint_details to verify the updated blueprint or open the UI URL.\n"
            f"Always show a link to the blueprint UI: "
            f"{self.get_blueprint_url(response.get('id', blueprint_uuid))}\n"
        )
        answer = (
            f"[ANSWER] Blueprint updated successfully: {{'UUID': '{response.get('id', blueprint_uuid)}'}}\n"
            "We could double check the details or start the build/compose"
        )
        return f"{instruction}{answer}"

    def get_blueprint_url(self, blueprint_id: str) -> str:
        """Get the URL for a blueprint."""
        return f"{self.insights_client.insights_base_url}/insights/image-builder/imagewizard/{blueprint_id}"

    async def get_blueprints(
        self,
        limit: Annotated[int, Field(7, description="Maximum number of items to return (use 7 as default)")],
        offset: Annotated[int, Field(0, description="Number of items to skip when paging (use 0 as default)")],
        search_string: Annotated[Optional[str], Field(None, description="Substring to search for in the name")],
    ) -> str:
        """🟢 List blueprints. Use limit/offset from the user. Paging hints in response footer."""

        # workaround seen in LLama 3.3 70B Instruct
        if search_string == "null":
            search_string = None

        limit = limit or self.default_response_size
        if limit <= 0:
            limit = self.default_response_size
        try:
            # Make request with limit and offset parameters
            params = {"limit": limit, "offset": offset}
            response = await self.insights_client.get("blueprints", params=params)

            if isinstance(response, str):
                return response

            if isinstance(response, list):
                raise InsightsApiError(
                    "Error: the response of get_blueprints is a list. This is not expected. "
                    f"Response: {json.dumps(response)}"
                )

            # Sort data by created_at
            sorted_data = sorted(response["data"], key=lambda x: x.get("last_modified_at", ""), reverse=True)

            ret: list[dict] = []
            for i, blueprint in enumerate(sorted_data, 1):
                data = {
                    "reply_id": i + offset,
                    "blueprint_uuid": blueprint["id"],
                    "UI_URL": self.get_blueprint_url(blueprint["id"]),
                    "name": blueprint["name"],
                }

                # Apply search filter if provided
                if search_string:
                    if search_string.lower() in data["name"].lower():
                        ret.append(data)
                else:
                    ret.append(data)

            intro = "[INSTRUCTION] Link each row using UI_URL.\n"
            intro += self._list_response_paging_instructions("get_blueprints", offset, len(ret))
            return f"{intro}\n{json.dumps(ret)}"
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(str(e)) from e

    async def get_blueprint_details(
        self, blueprint_identifier: Annotated[str, Field(description="The UUID, name or reply_id to query")]
    ) -> str:
        """🟢 Blueprint details by UUID, name, or reply_id from get_blueprints."""
        if not blueprint_identifier:
            raise InsightsApiError("Error: a blueprint identifier is required")

        try:
            # If the identifier looks like a UUID, use it directly
            if len(blueprint_identifier) == 36 and blueprint_identifier.count("-") == 4:
                response = await self.insights_client.get(f"blueprints/{blueprint_identifier}")
                if isinstance(response, dict):
                    return json.dumps([response])

                return json.dumps([{"error": "Unexpected list response", "data": response}])
            ret = f"[INSTRUCTION] Error: {blueprint_identifier} is not a valid blueprint identifier,"
            ret += "please use the UUID from get_blueprints\n"
            ret += "[INSTRUCTION] retry calling get_blueprints\n\n"
            ret += f"[ANSWER] {blueprint_identifier} is not a valid blueprint identifier"
            raise InsightsApiError(ret)
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(str(e)) from e

    def _create_compose_data(self, compose: dict, reply_id: int, client: InsightsClient) -> dict:
        """Create compose data dictionary with blueprint URL."""
        data = {
            "reply_id": reply_id,
            "compose_uuid": compose["id"],
            "blueprint_id": compose.get("blueprint_id", "N/A"),
            "image_name": compose.get("image_name", ""),
        }

        if compose.get("blueprint_id"):
            data["blueprint_url"] = (
                f"{client.insights_base_url}/insights/image-builder/imagewizard/{compose['blueprint_id']}"
            )
        else:
            data["blueprint_url"] = "N/A"

        return data

    def _should_include_compose(self, data: dict, search_string: Optional[str]) -> bool:
        """Determine if compose should be included based on search criteria."""
        if not search_string:
            return True
        return search_string.lower() in data["image_name"].lower()

    # NOTE: the _doc_ has escaped curly braces as __doc__.format() is called on the docstring
    async def get_composes(
        self,
        limit: Annotated[int, Field(7, description="Maximum number of items to return (use 7 as default)")],
        offset: Annotated[int, Field(0, description="Number of items to skip when paging (use 0 as default)")],
        search_string: Annotated[Optional[str], Field(None, description="Substring to search for in the name")],
    ) -> str:
        """🟢 Image build status, latest/recent compose builds, build jobs: use FIRST. Compose=build run."""
        limit = limit or self.default_response_size
        if limit <= 0:
            limit = self.default_response_size
        try:
            # Make request with limit and offset parameters
            params = {"limit": limit, "offset": offset}
            response = await self.insights_client.get("composes", params=params)

            if isinstance(response, str):
                return response

            if isinstance(response, list):
                raise InsightsApiError(
                    f"Error: the response of get_composes is a list. This is not expected. "
                    f"Response: {json.dumps(response)}"
                )

            # Sort data by created_at
            sorted_data = sorted(response["data"], key=lambda x: x.get("created_at", ""), reverse=True)

            ret: list[dict] = []
            for i, compose in enumerate(sorted_data, 1):
                data = self._create_compose_data(compose, i + offset, self.insights_client)

                # Apply search filter if provided
                if self._should_include_compose(data, search_string):
                    ret.append(data)

            intro = "[INSTRUCTION] Present a bulleted list; link each row with blueprint_url.\n"
            intro += self._list_response_paging_instructions("get_composes", offset, len(ret))
            intro += "[ANSWER]\n"
            return f"{intro}\n{json.dumps(ret)}"

        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(str(e)) from e

    # pylint: disable=too-many-return-statements
    async def get_compose_details(
        self, compose_identifier: Annotated[str, "The exact UUID string from get_composes()"]
    ) -> str:
        """🟢 One compose/image build status & details. UUID from get_composes—not "latest" alone."""
        if not compose_identifier:
            raise InsightsApiError("Error: Compose UUID is required")

        try:
            # If the identifier looks like a UUID, use it directly
            if len(compose_identifier) == 36 and compose_identifier.count("-") == 4:
                response = await self.insights_client.get(f"composes/{compose_identifier}")
                if isinstance(response, str):
                    return response

                if isinstance(response, list):
                    self.logger.error(
                        "Error: the response of get_compose_details is a list. "
                        "This is not expected. Response for %s: %s",
                        compose_identifier,
                        json.dumps(response),
                    )
                    raise InsightsApiError(f"Error: Unexpected list response for {compose_identifier}")
                response["compose_uuid"] = compose_identifier
            else:
                ret = (
                    f"[INSTRUCTION] Error: {compose_identifier} is not a valid compose identifier,"
                    "please use the UUID from get_composes\n"
                )
                ret += "[INSTRUCTION] retry calling get_composes\n\n"
                ret += f"[ANSWER] {compose_identifier} is not a valid compose identifier"
                raise InsightsApiError(ret)

            intro = ""
            download_url = response.get("image_status", {}).get("upload_status", {}).get("options", {}).get("url")
            upload_target = response.get("image_status", {}).get("upload_status", {}).get("type")
            image_name = response.get("image_status", {}).get("upload_status", {}).get("options", {}).get("image_name")

            if download_url and upload_target == "oci.objectstorage":
                intro += """
[INSTRUCTION] Leave the URL as code block so the user can copy and paste it.

To run the image copy the link below and follow the steps below:

   * Go to "Compute" in Oracle Cloud and choose "Custom Images".
   * Click on "Import image", choose "Import from an object storage URL".
   * Choose "Import from an object storage URL" and paste the URL in the "Object Storage URL" field.
        The image type has to be set to QCOW2 and the launch mode should be paravirtualized.

```
{download_url}
```
"""
            elif image_name and upload_target == "gcp":
                intro += f"""
[INSTRUCTION] present the two code blocks with their respective explanations below to the user.

To launch this image, contact your org admin to adjust your launch permissions.

Alternatively, launch directly from the cloud provider console.

Launch with Google Cloud Console:
```
gcloud compute instances create {image_name}-instance --image-project red-hat-image-builder --image {image_name}
```

or copy image to your account
```
gcloud compute images create {image_name}-copy --source-image-project red-hat-image-builder --source-image {image_name}
```
"""
            elif download_url:
                intro += f"The image is available at [{download_url}]({download_url})\n"
                intro += "Always present this link to the user\n"
            # else depends on the status and the target if it can be downloaded

            return f"{intro}{json.dumps(response)}"
        except InsightsApiError:
            raise
        except Exception as e:
            raise InsightsApiError(str(e)) from e


mcp_server = ImageBuilderMCP()
