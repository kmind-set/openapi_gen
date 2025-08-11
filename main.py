from _tool import OpenApiGenerator, SearchEndpointDeclaration
from example_service_endpoint import endpoint_config

generator = OpenApiGenerator(
    search_endpoint_declaration=SearchEndpointDeclaration.OneEndpointConfig,
    endpoint_config=endpoint_config,
    output_openapi_file="output_openapi.yaml",
)
generator.build_openapi_base("Service", "Description", "1.0")
generator.generate()
print(f"OpenAPI file generated at {generator.output_openapi_file}")
