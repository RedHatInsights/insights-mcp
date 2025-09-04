"""Image Builder MCP server for creating and managing Linux images."""

import json
import logging
import os
from typing import Annotated, Optional

import httpx
import jwt
from fastmcp.server.dependencies import get_http_headers
from fastmcp.tools.tool import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

from insights_mcp.client import InsightsClient
from insights_mcp.mcp import InsightsMCP
from tools import OpenAPIReducer

WATERMARK_CREATED = "Blueprint created via insights-mcp"
WATERMARK_UPDATED = "Blueprint updated via insights-mcp"


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

        self.paging_reminder = (
            "There could be more entries, ask the user if they want to get more"
            "and use the parameters offset and limit accordingly.\n"
        )

        general_intro = """You are a comprehensive Linux Image Builder assistant that creates custom
        Linux disk images, ISOs, and virtual machine images.

        You can build images for multiple Linux distributions including:
        - Red Hat Enterprise Linux (RHEL)
        - CentOS Stream
        - Fedora Linux (not an official version, only similar to upstream)

        You create various image formats suitable for:
        - Cloud deployments (AWS, Azure, GCP)
        - Virtual machines (VMware, guest images)
        - Edge computing devices
        - Container registries (OCI)
        - Bare metal installations (ISO installers)
        - WSL (Windows Subsystem for Linux)

        This service uses Red Hat's console.redhat.com image-builder osbuild.org infrastructure but serves
        general Linux image building needs across the entire ecosystem.

        🚨 CRITICAL BEHAVIORAL RULES:

        🟢 **CALL IMMEDIATELY** (tools marked with green indicator):
        - get_openapi, get_blueprints, get_blueprint_details, get_composes, get_compose_details
        - For queries like: "List my blueprints", "What's my build status?", "Show blueprint details"

        🔴 **GATHER INFORMATION FIRST** (tools marked with red indicator):
        - create_blueprint: Ask for name, distribution, architecture, image type, users, etc.

        🟡 **VERIFY PARAMETERS** (tools marked with yellow indicator):
        - blueprint_compose: Confirm blueprint UUID before proceeding

        **Note**: Each tool description includes color-coded behavioral indicators for MCP clients
                  that ignore server instructions.

        RULES FOR CREATION TOOLS:
        1. **ALWAYS GATHER COMPLETE INFORMATION FIRST** through a conversational approach
        2. **ASK SPECIFIC QUESTIONS** to collect all required details before making creation API calls
        3. **BE HELPFUL AND CONSULTATIVE** - guide users through the creation process
        4. **When you need to call a tool, you MUST use the tool_calls format, NOT plain text.**

        WHEN A USER ASKS TO CREATE AN IMAGE OR ISO:
        - Start by asking about their specific needs and use case
        - Ask for blueprint name, distribution, architecture, image type, etc.
        - For RHEL images: Always ask about registration preferences
        - Ask about custom user accounts and any special configurations
        - Only call create_blueprint() after you have ALL required information

        Your goal is to be a knowledgeable consultant who helps users both access existing information
        immediately and create the perfect custom Linux image, ISO, or virtual machine image for their
        specific deployment needs.

        🚨 **CRITICAL REPOSITORY HANDLING**:
        When users want to add custom repositories to their blueprints, you MUST:
        1. Use `content-sources_list_repositories` to find repository UUIDs
        2. Include the SAME repository UUIDs in BOTH payload_repositories AND custom_repositories fields
        3. This dual inclusion is MANDATORY - missing either field causes build failures
        4. NEVER make up or guess repository UUIDs - ALWAYS use the actual UUIDs from content-sources_list_repositories

        <|function_call_library|>

        """

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

    def _get_image_types_architectures(self) -> tuple[list[str], list[str]] | None:
        """Get the list of image types available to build images with."""
        try:
            # TBD: change openapi spec to have a proper schema-enum
            # for image types and architectures
            self.logger.info("Getting openapi")
            openapi = json.loads(self.get_openapi_synchronous())

            image_types = list(openapi["components"]["schemas"]["ImageTypes"]["enum"])
            image_types.sort()

            architectures = list(openapi["components"]["schemas"]["ImageRequest"]["properties"]["architecture"]["enum"])
            architectures.sort()

            self.logger.info("Supported image types: %s", image_types)
            self.logger.info("Supported architectures: %s", architectures)
        except Exception as e:  # pylint: disable=broad-exception-caught
            raise ValueError("Error getting openapi for image types and architectures") from e
        return image_types, architectures

    def register_tools(self):
        """Register all available tools with the MCP server."""
        image_types, architectures = self._get_image_types_architectures()
        if not image_types or not architectures:
            return

        # prepend generic keywords for use of many other tools
        # and register with "self.tool()"
        tool_functions = [
            self.get_openapi,
            self.create_blueprint,
            self.update_blueprint,
            self.get_blueprints,
            self.get_blueprint_details,
            self.get_composes,
            self.get_compose_details,
            self.blueprint_compose,
            self.get_distributions,
        ]

        for f in tool_functions:
            tool = Tool.from_function(f)
            tool.annotations = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
            description_str = f.__doc__.format(
                architectures=", ".join(architectures), image_types=", ".join(image_types)
            )
            tool.description = description_str
            tool.title = description_str.split("\n", 1)[0]
            self.add_tool(tool)

    async def get_distributions(self) -> str:
        """Get the list of distributions available to build images with.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Emphasize that there is support only for Red Hat Enterprise Linux (RHEL) images
        and there only for the latest minor version of each major version.
        Emphasize that Fedora images are "similar" to the upstream but no official versions!
        Emphasize that CentOS Stream is not supported by Red Hat.

        Returns:
            List of distributions
        """
        try:
            client = self.get_client(get_http_headers())
        except ValueError as e:
            return self.no_auth_error(e)

        try:
            distributions = await client.get("distributions")
            return json.dumps(distributions)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error getting distributions: {str(e)}"

    def get_client_id(self, headers: dict[str, str]) -> str:
        """Get the client ID preferably from the headers."""
        client_id = self.insights_client.client_id or ""
        if self.insights_client.oauth_enabled:
            caller_headers_auth = headers.get("authorization")
            if caller_headers_auth and caller_headers_auth.startswith("Bearer "):
                # decode bearer token to get sid and use as client_id
                token = caller_headers_auth.split("Bearer ", 1)[-1]
                client_id = jwt.decode(token, options={"verify_signature": False}).get("sid")
                self.logger.debug("Using sid from Bearer token as client_id: %s", client_id)
        else:
            client_id = headers.get("insights-client-id") or self.insights_client.client_id or ""
            self.logger.debug("get_client_id request headers: %s", headers)

        # explicit check for mypy
        if not client_id:
            raise ValueError("Client ID is required to access the Image Builder API")
        return client_id

    def get_client_secret(self, headers: dict[str, str]) -> str:
        """Get the client secret preferably from the headers."""
        client_secret = headers.get("insights-client-secret") or self.insights_client.client_secret
        self.logger.debug("get_client_secret request headers: %s", headers)

        if not client_secret:
            raise ValueError("Client secret is required to access the Image Builder API")
        return client_secret

    def get_client(self, headers: dict[str, str]) -> InsightsClient:
        """Get the InsightsClient instance for the current user."""
        client_id = self.get_client_id(headers)
        client = self.clients.get(client_id)
        if not client:
            client_secret = None
            if not self.insights_client.oauth_enabled:
                client_secret = self.get_client_secret(headers)
            client = InsightsClient(
                api_path="api/image-builder/v1",
                client_id=client_id,
                client_secret=client_secret,
                mcp_transport=self.insights_client.mcp_transport,
                oauth_enabled=self.insights_client.oauth_enabled,
                headers={"X-ImageBuilder-ui": self.image_builder_mcp_client_id},
                proxy_url=self.insights_client.proxy_url,
            )
            self.clients[client_id] = client
        return client

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
        return httpx.get(f"{base_url}/{api_path}/openapi.json", timeout=60).text

    def no_auth_error(self, e: httpx.HTTPStatusError | ValueError) -> str:
        """Generate authentication error message based on transport type."""
        return self.insights_client.client.no_auth_error(e)

    async def blueprint_compose(
        self, blueprint_uuid: Annotated[str, Field(description="The UUID of the blueprint to compose")]
    ) -> str:
        """Compose an image from a blueprint UUID created with create_blueprint, get_blueprints.
        If the UUID is not clear, ask the user whether to create a new blueprint with create_blueprint
        or use an existing blueprint from get_blueprints.

        🟡 VERIFY PARAMETERS - Confirm blueprint UUID before proceeding.

        Returns:
            The response from the image-builder API

        Raises:
        """
        try:
            client = self.get_client(get_http_headers())
        except ValueError as e:
            return self.no_auth_error(e)

        try:
            response = await client.post(f"blueprints/{blueprint_uuid}/compose")
        # avoid crashing the server so we'll stick to the broad exception catch
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error: {str(e)} in blueprint_compose {blueprint_uuid}"

        response_str = "[INSTRUCTION] Use the tool get_compose_details to get the details of the compose\n"
        response_str += "like the current build status\n"
        response_str += "[ANSWER] Compose created successfully:"
        build_ids_str: list[str] = []

        if isinstance(response, dict):
            return (
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
        """Get OpenAPI spec. Use this to get details e.g for a new blueprint

        🟢 CALL IMMEDIATELY - No information gathering required.

        Optional parameters:
        - **endpoints**: Comma-separated endpoint specs (like `GET:/blueprints,POST:/blueprints`).
          When provided, the returned OpenAPI is minimized to only the selected paths and their transitive
          component references. Use this only to prepare payloads for `create_blueprint` or `update_blueprint`.

        Returns:
            OpenAPI specification JSON (possibly reduced when 'endpoints' is provided)

        Raises:
            Exception: If the image-builder connection fails.
        """
        try:
            response = await self.insights_client.get("openapi.json", noauth=True)
            if endpoints:
                try:
                    endpoint_list = [e.strip() for e in endpoints.split(",") if e.strip()]
                    reducer = OpenAPIReducer.from_response(response)
                    reduced = reducer.reduce(endpoint_list)
                    return json.dumps(reduced)
                except Exception as reduce_err:  # pylint: disable=broad-exception-caught
                    # Fall back to full spec on any reduction error
                    self.logger.warning("OpenAPI reduction failed: %s", reduce_err)
                    return json.dumps(response)
            return json.dumps(response)
        # avoid crashing the server so we'll stick to the broad exception catch
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error: {str(e)}"

    async def create_blueprint(
        self,
        data: Annotated[
            dict,
            Field(description="Complete blueprint data formatted according to CreateBlueprintRequest from get_openapi"),
        ],
    ) -> str:
        """Create a custom Linux image blueprint.

        🔴 GATHER INFORMATION FIRST - Do not call immediately.
        ⚠️ CRITICAL: Only call this function after you have gathered ALL required information from the user.

        INFORMATION YOU MUST COLLECT FROM THE USER BEFORE CALLING:
        1. Blueprint name ("What would you like to name your blueprint? or should I generate a name?")
        2. Distribution ("Which distribution do you want? call get_distributions to see the list of distributions")
        3. Architecture ("Which architecture? Available: {architectures}")
        4. Image type ("What image type do you need? Available: {image_types} or take guest-image as default")
        5. Username ("Do you want to create a custom user account? If so, what username?")
        6. For RHEL images specifically: "Do you want to enable registration for Red Hat services?"
        7. Any customizations ("Do you need any specific packages, services, or configurations?")

        🚨 CRITICAL REPOSITORY REQUIREMENT:
        ⚠️ **CUSTOM REPOSITORIES MUST BE INCLUDED IN BOTH FIELDS**:
        When adding custom repositories to a blueprint, you MUST include them in BOTH:
        - payload_repositories - for package installation during build
        - custom_repositories - for repository configuration in the final image

        This dual inclusion is REQUIRED for the blueprint to work correctly.
        Missing either field will cause build failures.

        📋 REPOSITORY SETUP PROCESS:
        1. Use content_sources_mcp tool to find repository UUIDs: `content-sources_list_repositories`
        2. Include the same repository UUIDs in BOTH payload_repositories and custom_repositories arrays
           along with their URL
        3. NEVER use fake or made-up UUIDs - ALWAYS get real UUIDs from the content-sources tool
        4. Example structure:
           ```json
           {{
             "payload_repositories": [
               {{"id": "repo-uuid-1", "url": "https://repo-url-1"}},
               {{"id": "repo-uuid-2", "url": "https://repo-url-2"}}
              ],
             "custom_repositories": [
               {{"id": "repo-uuid-1", "url": "https://repo-url-1"}},
               {{"id": "repo-uuid-2", "url": "https://repo-url-2"}}
             ]
           }}
           ```

        NOTES ON CUSTOMIZATIONS:
        1. If you need to add custom repositories, pass them in as payload_repositories AND custom_repositories
        2. For custom_repositories and payload_repositories, its best to store the UUID from the repositories in
           the content_sources_mcp tool
        3. CRITICAL: NEVER use fake or made-up repository UUIDs. ALWAYS call content-sources_list_repositories
           to get real UUIDs

        YOUR PROCESS AS THE AI ASSISTANT:
        1. If you haven't already, call get_openapi to understand the CreateBlueprintRequest structure.
           For minimal context, call `get_openapi(endpoints="POST:/blueprints")` when preparing the payload.
        2. only for registration, call get_blueprints and get_blueprint_details to guess the "organization" value
        4. Ask the user for ALL the required information listed above through conversation
        5. Only after collecting all information, call this function with properly formatted data

        Never make assumptions or fill in data yourself unless the user explicitly asks for it.
        Always ask the user for explicit input through conversation.

        Returns:
            The response from the image-builder API
        """
        try:
            client = self.get_client(get_http_headers())
        except ValueError as e:
            return self.no_auth_error(e)
        try:
            if os.environ.get("IMAGE_BUILDER_MCP_DISABLE_DESCRIPTION_WATERMARK", "").lower() != "true":
                desc_parts = [data.get("description", ""), WATERMARK_CREATED]
                data["description"] = "\n".join(filter(None, desc_parts))
            # TBD: programmatically check against openapi
            response = await client.post("blueprints", json=data)
        # avoid crashing the server so we'll stick to the broad exception catch
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error: {str(e)}"

        if isinstance(response, str):
            return response

        if isinstance(response, list):
            return (
                "Error: the response of blueprint creation is a list. This is not expected. "
                f"Response: {json.dumps(response)}"
            )

        response_str = "[INSTRUCTION] Use the tool get_blueprint_details to get the details of the blueprint\n"
        response_str += "or ask the user to start the build/compose with blueprint_compose\n"
        response_str += f"Always show a link to the blueprint UI: {self.get_blueprint_url(client, response['id'])}\n"
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
        """Update a blueprint.

        🟡 VERIFY PARAMETERS - Get original blueprint details and UUID before proceeding.

        Guidance for LLM:
        - Use `get_openapi(endpoints="PUT:/blueprints/{{id}}")` to fetch the minimal schema needed to format the
          update payload (path placeholders are acceptable in endpoint specs).

        Returns:
            The response from the image-builder API
        """
        try:
            client = self.get_client(get_http_headers())
        except ValueError as e:
            return self.no_auth_error(e)

        try:
            if os.environ.get("IMAGE_BUILDER_MCP_DISABLE_DESCRIPTION_WATERMARK", "").lower() != "true":
                if all(wmark not in data.get("description", "") for wmark in [WATERMARK_CREATED, WATERMARK_UPDATED]):
                    desc_parts = [data.get("description", ""), WATERMARK_UPDATED]
                    data["description"] = "\n".join(filter(None, desc_parts))
            response = await client.put(f"blueprints/{blueprint_uuid}", json=data)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error: {str(e)}"

        # Normalize response handling similar to create_blueprint
        if isinstance(response, str):
            return response

        if isinstance(response, list):
            return (
                "Error: the response of blueprint update is a list. This is not expected. "
                f"Response: {json.dumps(response)}"
            )

        # Build an instructional answer with a UI link like in create_blueprint
        instruction = (
            "[INSTRUCTION] Use the tool get_blueprint_details to verify the updated blueprint or open the UI URL.\n"
            f"Always show a link to the blueprint UI: "
            f"{self.get_blueprint_url(client, response.get('id', blueprint_uuid))}\n"
        )
        answer = (
            f"[ANSWER] Blueprint updated successfully: {{'UUID': '{response.get('id', blueprint_uuid)}'}}\n"
            "We could double check the details or start the build/compose"
        )
        return f"{instruction}{answer}"

    def get_blueprint_url(self, client: InsightsClient, blueprint_id: str) -> str:
        """Get the URL for a blueprint."""
        return f"{client.insights_base_url}/insights/image-builder/imagewizard/{blueprint_id}"

    async def get_blueprints(
        self,
        limit: Annotated[int, Field(7, description="Maximum number of items to return (use 7 as default)")],
        offset: Annotated[int, Field(0, description="Number of items to skip when paging (use 0 as default)")],
        search_string: Annotated[Optional[str], Field(None, description="Substring to search for in the name")],
    ) -> str:
        """Show user's image blueprints (saved image templates/configurations for
        Linux distributions, packages, users).

        🟢 CALL IMMEDIATELY - No information gathering required.
        """

        try:
            client = self.get_client(get_http_headers())
        except ValueError as e:
            return self.no_auth_error(e)

        # workaround seen in LLama 3.3 70B Instruct
        if search_string == "null":
            search_string = None

        limit = limit or self.default_response_size
        if limit <= 0:
            limit = self.default_response_size
        try:
            # Make request with limit and offset parameters
            params = {"limit": limit, "offset": offset}
            response = await client.get("blueprints", params=params)

            if isinstance(response, str):
                return response

            if isinstance(response, list):
                return (
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
                    "UI_URL": self.get_blueprint_url(client, blueprint["id"]),
                    "name": blueprint["name"],
                }

                # Apply search filter if provided
                if search_string:
                    if search_string.lower() in data["name"].lower():
                        ret.append(data)
                else:
                    ret.append(data)

            intro = "[INSTRUCTION] Use the UI_URL to link to the blueprint\n"
            intro += self.paging_reminder
            return f"{intro}\n{json.dumps(ret)}"
        # avoid crashing the server so we'll stick to the broad exception catch
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error: {str(e)}"

    async def get_blueprint_details(
        self, blueprint_identifier: Annotated[str, Field(description="The UUID, name or reply_id to query")]
    ) -> str:
        """Get blueprint details.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Returns:
            Blueprint details

        Raises:
            Exception: If the image-builder connection fails.
        """
        if not blueprint_identifier:
            return "Error: a blueprint identifier is required"
        try:
            client = self.get_client(get_http_headers())
        except ValueError as e:
            return self.no_auth_error(e)

        try:
            # If the identifier looks like a UUID, use it directly
            if len(blueprint_identifier) == 36 and blueprint_identifier.count("-") == 4:
                response = await client.get(f"blueprints/{blueprint_identifier}")
                if isinstance(response, dict):
                    return json.dumps([response])

                return json.dumps([{"error": "Unexpected list response", "data": response}])
            ret = f"[INSTRUCTION] Error: {blueprint_identifier} is not a valid blueprint identifier,"
            ret += "please use the UUID from get_blueprints\n"
            ret += "[INSTRUCTION] retry calling get_blueprints\n\n"
            ret += f"[ANSWER] {blueprint_identifier} is not a valid blueprint identifier"
            return ret
        # avoid crashing the server so we'll stick to the broad exception catch
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error: {str(e)}"

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
        """Get a list of all image builds (composes) with their UUIDs and basic status.

        **ALWAYS USE THIS FIRST** when checking image build status or finding builds.
        This returns the UUID needed for get_compose_details.
        🟢 CALL IMMEDIATELY - No information gathering required.

        Common uses:
        - Check status of recent builds → call this first
        - Find your latest build → call this first
        - Get any build information → call this first
        Ask the user if they want to get more composes and adapt "offset" accordingly.

        You can also provide this link so the user can check directly in the UI:
        https://console.redhat.com/insights/image-builder

        Returns:
            List of composes with:
            - uuid: The unique identifier (REQUIRED for get_compose_details)
            - name: Blueprint name used
            - status: Current build status
            - created_at: When the build started

        Example response:
        [
            {{
                "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "my-rhel-image",
                "status": "RUNNING",
                "created_at": "2025-01-18T10:30:00Z"
            }}
        ]
        """
        limit = limit or self.default_response_size
        if limit <= 0:
            limit = self.default_response_size
        try:
            client = self.get_client(get_http_headers())

            # Make request with limit and offset parameters
            params = {"limit": limit, "offset": offset}
            response = await client.get("composes", params=params)

            if isinstance(response, str):
                return response

            if isinstance(response, list):
                return (
                    f"Error: the response of get_composes is a list. This is not expected. "
                    f"Response: {json.dumps(response)}"
                )

            # Sort data by created_at
            sorted_data = sorted(response["data"], key=lambda x: x.get("created_at", ""), reverse=True)

            ret: list[dict] = []
            for i, compose in enumerate(sorted_data, 1):
                data = self._create_compose_data(compose, i + offset, client)

                # Apply search filter if provided
                if self._should_include_compose(data, search_string):
                    ret.append(data)

            intro = (
                "[INSTRUCTION] Present a bulleted list and use the blueprint_url to link to the "
                "blueprint which created this compose\n"
            )
            intro += self.paging_reminder
            intro += "[ANSWER]\n"
            return f"{intro}\n{json.dumps(ret)}"

        except ValueError as e:
            return self.no_auth_error(e)
        # avoid crashing the server so we'll stick to the broad exception catch
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error: {str(e)}"

    # pylint: disable=too-many-return-statements
    async def get_compose_details(
        self, compose_identifier: Annotated[str, "The exact UUID string from get_composes()"]
    ) -> str:
        """Get detailed information about a specific image build.

        ⚠️ REQUIRES: You MUST have the compose UUID from get_composes() first.
        ⚠️ NEVER call this with generic terms like "latest", "recent", or "my build"
        🟢 CALL IMMEDIATELY - No information gathering required.

        Process:
        1. User asks about build status → call get_composes()
        2. Find the desired compose and copy its UUID
        3. Call this function with that exact UUID

        Returns:
            Detailed compose information including:
            - Full status and progress
            - Error messages if failed
            - Download URLs if completed
            - Build logs
            - Artifact details
        """
        if not compose_identifier:
            return "Error: Compose UUID is required"
        try:
            client = self.get_client(get_http_headers())
        except ValueError as e:
            return self.no_auth_error(e)

        try:
            # If the identifier looks like a UUID, use it directly
            if len(compose_identifier) == 36 and compose_identifier.count("-") == 4:
                response = await client.get(f"composes/{compose_identifier}")
                if isinstance(response, str):
                    return response

                if isinstance(response, list):
                    self.logger.error(
                        "Error: the response of get_compose_details is a list. "
                        "This is not expected. Response for %s: %s",
                        compose_identifier,
                        json.dumps(response),
                    )
                    return f"Error: Unexpected list response for {compose_identifier}"
                response["compose_uuid"] = compose_identifier
            else:
                ret = (
                    f"[INSTRUCTION] Error: {compose_identifier} is not a valid compose identifier,"
                    "please use the UUID from get_composes\n"
                )
                ret += "[INSTRUCTION] retry calling get_composes\n\n"
                ret += f"[ANSWER] {compose_identifier} is not a valid compose identifier"
                return ret

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
        # avoid crashing the server so we'll stick to the broad exception catch
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error: {e}"


mcp_server = ImageBuilderMCP()
