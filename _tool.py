import copy
import dataclasses
import logging
import enum
import inspect
import types
import typing
from typing import (
    Any,
    Dict,
    List,
    Tuple,
    Optional,
    get_args,
    get_origin,
    get_type_hints,
)

import yaml

from utils import deep_change_keys_by_format, snake_case_to_camel_case
from gen_types import GeneratorConfig


class SearchEndpointDeclaration(enum.Enum):
    OneEndpointConfig = "OneEndpointConfig"


class OpenApiGenerator:
    def __init__(
        self,
        openapi_version: str = "3.1.0",
        search_endpoint_declaration: SearchEndpointDeclaration = SearchEndpointDeclaration.OneEndpointConfig,
        output_openapi_file: str = "output_openapi.yaml",
        to_camel_case_schemas: bool = True,
        endpoint_config: GeneratorConfig | None = None,
    ):
        if search_endpoint_declaration not in SearchEndpointDeclaration:
            raise ValueError(
                f"Invalid search endpoint declaration: {search_endpoint_declaration}"
            )

        self.output_openapi_file = output_openapi_file
        self.search_endpoint_declaration = search_endpoint_declaration

        if search_endpoint_declaration == SearchEndpointDeclaration.OneEndpointConfig:
            if not endpoint_config:
                raise ValueError(
                    "GeneratorConfig is required when using GeneratorConfig search endpoint declaration."
                )
            self.endpoint_config = [endpoint_config]

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.openapi_version = openapi_version
        self.openapi_build = None

        self.to_camel_case_schemas = to_camel_case_schemas

    @staticmethod
    def is_optional(tp: Any) -> bool:
        return (
            (get_origin(tp) is typing.Union and type(None) in get_args(tp))
            or (get_origin(tp) is typing.Optional and len(get_args(tp)) == 1)
            or (get_origin(tp) is types.UnionType and type(None) in get_args(tp))
        )

    @staticmethod
    def type_to_schema(
        _target_type: Any, known_defs: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:

        if get_origin(_target_type) in (typing.Union, types.UnionType):
            args = [a for a in get_args(_target_type) if a is not type(None)]

            if len(args) == 1:
                return OpenApiGenerator.type_to_schema(args[0], known_defs)
            return {
                "oneOf": [
                    OpenApiGenerator.type_to_schema(a, known_defs)[0] for a in args
                ]
            }, known_defs

        if get_origin(_target_type) in (list, typing.List):
            item_type = get_args(_target_type)[0]
            items_schema, defs = OpenApiGenerator.type_to_schema(item_type, known_defs)
            return {"type": "array", "items": items_schema}, defs

        if inspect.isclass(_target_type) and issubclass(_target_type, enum.Enum):
            return {
                "type": "string",
                "enum": [e.value for e in _target_type],
            }, known_defs

        if dataclasses.is_dataclass(_target_type):

            name = getattr(_target_type, "__name__", type(_target_type).__name__)
            if name not in known_defs:
                schema, _ = OpenApiGenerator.dataclass_to_openapi_schema(
                    _target_type, known_defs
                )
                known_defs[name] = schema
            return {"$ref": f"#/components/schemas/{name}"}, known_defs

        if _target_type is str:
            return {"type": "string"}, known_defs
        if _target_type is int:
            return {"type": "integer"}, known_defs
        if _target_type is float:
            return {"type": "number"}, known_defs
        if _target_type is bool:
            return {"type": "boolean"}, known_defs

        return {"type": "string"}, known_defs

    @staticmethod
    def dataclass_to_openapi_schema(
        cls: Any, root_types: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if root_types is None:
            root_types = {}
        props = {}
        required = []
        for field in dataclasses.fields(cls):
            if field.name.startswith("_"):
                continue
            field_type = field.type
            prop_schema, defs = OpenApiGenerator.type_to_schema(field_type, root_types)
            props[field.name] = prop_schema
            if not OpenApiGenerator.is_optional(field_type):
                required.append(field.name)
            root_types.update(defs)

        schema = {"type": "object", "properties": props}
        if required:
            schema["required"] = required

        root_types[cls.__name__] = schema
        return schema, root_types

    def build_openapi_base(self, title, description, version) -> Dict[str, Any]:
        self.openapi_build = {
            "openapi": self.openapi_version,
            "info": {"title": title, "description": description, "version": version},
            "components": {
                "schemas": {},
                "parameters": {},
                "responses": {},
                "examples": {},
            },
            "paths": {},
        }

    def getPaths(self) -> Dict[str, Any]:
        return self.openapi_build.get("paths", {})

    def getComponents(self) -> Dict[str, Any]:
        return self.openapi_build.get("components", {})

    def getSchemas(self) -> Dict[str, Any]:
        return self.openapi_build.get("components", {}).get("schemas", {})

    def setSchemas(self, schemas: Dict[str, Any]) -> None:
        if "components" not in self.openapi_build:
            self.openapi_build["components"] = {}
        if (
            "schemas" not in self.openapi_build["components"]
            or self.openapi_build["components"]["schemas"] is None
        ):
            self.openapi_build["components"]["schemas"] = {}

        if self.to_camel_case_schemas:
            schemas = deep_change_keys_by_format(schemas, snake_case_to_camel_case)
            self.openapi_build["components"]["schemas"].update(schemas)

        else:
            self.openapi_build["components"]["schemas"].update(schemas)

    def addPath(self, newPath):
        if newPath not in self.getPaths():
            self.getPaths()[newPath] = {}

    def getPath(self, path):
        return self.getPaths()[path]

    def process_services(self, services_info: List[GeneratorConfig]) -> None:
        for service in services_info:

            service_name = service.serviceName

            httpPath = (
                service.httpPath
                if service.httpPath.startswith("/")
                else f"/{service.httpPath}"
            )
            httpMethod = service.httpMethod.lower()

            self.addPath(httpPath)

            targetPath = self.getPath(httpPath)

            targetPath[httpMethod] = {
                "operationId": service.operationId,
                "summary": service.description,
                "responses": {},
            }

            httpMethodInfo = targetPath[httpMethod]
            inputSchema = service.serviceInput

            if not inputSchema:
                raise ValueError(f"Input schema not found for service {service_name}")

            domainName = getattr(inputSchema, "domainName", "_").capitalize()

            outputSchema = service.serviceOutput

            if not outputSchema:
                raise ValueError(f"Output schema not found for service {service_name}")

            _schema, defs = OpenApiGenerator.dataclass_to_openapi_schema(inputSchema)
            print(_schema["properties"])
            self.setSchemas(_schema["properties"])
            if "domainName" in self.getSchemas():
                self.getSchemas().pop("domainName")

            if "pathPatameters" in self.getSchemas():
                if "$ref" in self.getSchemas()["pathPatameters"]:
                    self.getSchemas().pop("pathPatameters")

            if "queryStringParameters" in self.getSchemas():
                if "$ref" in self.getSchemas()["queryStringParameters"]:
                    self.getSchemas().pop("queryStringParameters")

            self.setSchemas(defs)

            _schema, defs = OpenApiGenerator.dataclass_to_openapi_schema(outputSchema)

            self.setSchemas(defs)

            httpMethodInfo["parameters"] = []
            parameters = {}
            queryParamsTarget = (
                "queryStringParameters"
                if "queryStringParameters" in self.getSchemas()
                and not "$ref" in self.getSchemas()["queryStringParameters"]
                else "QueryStringParameters"
            )
            if queryParamsTarget in self.getSchemas():
                queryParametersKey = f"{domainName}QueryStringParameters"
                self.getSchemas()[queryParametersKey] = self.getSchemas().pop(
                    queryParamsTarget
                )

                parameters[queryParametersKey] = {
                    "name": queryParametersKey,
                    "in": "query",
                    "required": False,
                    "schema": {"$ref": f"#/components/schemas/{queryParametersKey}"},
                }

                httpMethodInfo["parameters"].append(
                    {"$ref": f"#/components/parameters/{queryParametersKey}"}
                )

                if "queryStringParameters" in self.getSchemas():
                    self.getSchemas().pop("queryStringParameters")
                    pass

            pathParamTarget = (
                "pathParameters"
                if "pathParameters" in self.getSchemas()
                and not "$ref" in self.getSchemas()["pathParameters"]
                else "PathParameters"
            )
            pathParametersKey = None
            if pathParamTarget in self.getSchemas():
                pathParametersKey = f"{domainName}PathParameters"
                self.getSchemas()[pathParametersKey] = self.getSchemas().pop(
                    pathParamTarget
                )

                _properties = self.getSchemas()[pathParametersKey]["properties"]

                for key, value in _properties.items():
                    self.getSchemas()[f"{pathParametersKey}{key}"] = copy.deepcopy(
                        value
                    )
                    parameters[f"{pathParametersKey}{key}"] = {
                        "name": f"{key}",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "$ref": f"#/components/schemas/{f'{pathParametersKey}{key}'}"
                        },
                    }
                    httpMethodInfo["parameters"].append(
                        {
                            "$ref": f"#/components/parameters/{f'{pathParametersKey}{key}'}"
                        }
                    )
                if "pathParameters" in self.getSchemas():
                    self.getSchemas().pop("pathParameters")

                self.getSchemas().pop(pathParametersKey)

            bodyInputTarget = (
                "bodyInput"
                if "bodyInput" in self.getSchemas()
                and not "$ref" in self.getSchemas()["bodyInput"]
                else "BodyInput"
            )
            if bodyInputTarget in self.getSchemas():
                bodyInputKey = f"{domainName}BodyInput"
                self.getSchemas()[bodyInputKey] = self.getSchemas().pop(bodyInputTarget)
                if "bodyInput" in self.getSchemas():
                    self.getSchemas().pop("bodyInput")

            if service.serviceInput.__name__ in self.getSchemas():

                self.getSchemas().pop(service.serviceInput.__name__)

            if service.serviceInput.bodyInput:

                request_body = {
                    "description": "Request body",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{bodyInputKey}"}
                        }
                    },
                }
                httpMethodInfo["requestBody"] = request_body

            self.getComponents()["parameters"] |= parameters

            if service.serviceOutput:
                httpMethodInfo["responses"] = {}
                _name = service.serviceOutput.__name__

                httpMethodInfo["responses"][_name] = {}

                if dataclasses.is_dataclass(service.serviceOutput):
                    _, defs = OpenApiGenerator.dataclass_to_openapi_schema(
                        service.serviceOutput
                    )
                    self.setSchemas(defs)

                self.getSchemas().pop(_name)

                inspectBody = get_type_hints(service.serviceOutput)

                inspectBody = inspectBody.get("bodyOutput")
                self.getSchemas()[
                    f"{domainName}{inspectBody.__name__}"
                ] = self.getSchemas().pop(inspectBody.__name__)
                inspectContent = [
                    field
                    for field in dataclasses.fields(inspectBody)
                    if field.name == "_contentType"
                ][0].default

                httpMethodInfo["responses"] = {}
                httpMethodInfo["responses"][200] = {}
                httpMethodInfo["responses"][200]["content"] = {}
                httpMethodInfo["responses"][200]["description"] = "Success"
                _content = httpMethodInfo["responses"][200]["content"]
                _content[inspectContent] = {
                    "schema": {
                        "$ref": f"#/components/schemas/{domainName}{inspectBody.__name__}"
                    }
                }

    def generate(self):

        if self.openapi_build is None:
            raise ValueError("OpenAPI build is not initialized.")

        if (
            self.search_endpoint_declaration
            == SearchEndpointDeclaration.OneEndpointConfig
        ):
            self.process_services(self.endpoint_config)

        with open(self.output_openapi_file, "w") as f:
            yaml.dump(
                self.openapi_build, f, sort_keys=False, allow_unicode=True, indent=2
            )
