from typing import Any, Callable, Union


def snake_case_to_camel_case(string):

    return "".join(
        [
            w if (idx == 0) else f"{w[0].capitalize()}{w[1:]}"
            for idx, w in enumerate(string.split("_"))
            if w
        ]
    )
def deep_change_keys_by_format(entity: Union[dict, list, Any], format: Callable):


    if isinstance(entity, list):
        return [deep_change_keys_by_format(item, format) for item in entity]
    elif isinstance(entity, dict):
        new_dict = {}
        for key, value in entity.items():
            new_key = format(key)
            new_dict[new_key] = deep_change_keys_by_format(value, format)
        return new_dict

    else:
        return entity
