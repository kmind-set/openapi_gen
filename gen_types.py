
from dataclasses import dataclass
import inspect
from typing import Type, TypeVar, Generic
from typing import Protocol

class DataclassProtocol(Protocol):
    @classmethod
    def from_dict(cls, attrs: dict):      
        return cls(**{
            k: v for k, v in attrs.items() 
            if k in inspect.signature(cls).parameters
        })

QP = TypeVar("QP", bound=DataclassProtocol)
B = TypeVar("B", bound=DataclassProtocol)
PP = TypeVar("PP", bound=DataclassProtocol)
H = TypeVar("H", bound=DataclassProtocol)

class AbstractInput(Generic[QP, B,PP, H]):
    queryStringParameters: QP | None = None
    bodyInput: B | None = None
    pathParameters: PP | None = None
    headers: H | None = None

    def _class_getitem_(cls, generic_type):
        new_cls = type(cls._name, cls.bases, dict(cls.dict_))
        new_cls._QP = generic_type[0] if len(generic_type) > 0 else None
        new_cls._B  = generic_type[1] if len(generic_type) > 1 else None
        new_cls._PP = generic_type[2] if len(generic_type) > 2 else None
        new_cls._H = generic_type[3] if len(generic_type) > 3 else None
        return new_cls

OB = TypeVar("OB")

@dataclass
class StatusCode:
    statusCode: int

class AbstractOutput(Generic[OB]):
    bodyOutput: OB

    def _class_getitem_(cls, generic_type):
        new_cls = type(cls._name, cls.bases, dict(cls.dict_))
        new_cls._OB = generic_type[0] if len(generic_type) > 0 else None

        return new_cls
 
@dataclass
class GeneratorConfig:
    serviceName: str
    description: str
    operationId: str
    httpMethod: str
    httpPath: str
    serviceInput: Type[AbstractInput]
    serviceOutput: Type[AbstractOutput] 
