
from dataclasses import dataclass
from typing import TypeAlias
from gen_types import AbstractInput, AbstractOutput, GeneratorConfig

@dataclass
class QueryStringParametersUser():
    user: str

@dataclass
class QueryStringParametersOrganization():
    organizationName: str

@dataclass
class PathParameters():
    userId: str

@dataclass
class OutputBody:
    code: int
    message: str
    response: dict
    _contentType: str = "application/json"
QueryStringParameters: TypeAlias = QueryStringParametersUser | QueryStringParametersOrganization

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
def my_endpoint(event, context):
    return {"statusCode": 200, "body": "Hello, world!"}