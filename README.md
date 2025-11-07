## OpenApi Generator

## Example

```python

@dataclass
class RequestSchema( AbstractInput[QueryStringParametersUser | QueryStringParametersOrganization, None, PathParameters, None]):
    domainName: str = "_"
    queryStringParameters: QueryStringParametersUser | QueryStringParametersOrganization
    pathParameters: PathParameters


@dataclass
class ResponseSchema(AbstractOutput[OutputBody]):
    bodyOutput: OutputBody


endpoint_config = GeneratorConfig(
    serviceInput=RequestSchema,
    serviceOutput=ResponseSchema,
    serviceName="MyService",
    description="My service description",
    operationId="myEndpoint",
    httpMethod="GET",
    httpPath="world/{userId}"

)
generator = OpenApiGenerator(
    search_endpoint_declaration=SearchEndpointDeclaration.OneEndpointConfig,
    endpoint_config=endpoint_config,
    output_openapi_file="output_openapi.yaml",
)
generator.build_openapi_base("Service", "Description", "1.0")
generator.generate()
```
