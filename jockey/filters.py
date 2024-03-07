import re
from functools import wraps
from typing import Any, Callable, Dict, List, Tuple, Type, TypeVar


T = TypeVar('T')
JockeyFilter = Callable[[T, T], bool]


def equals_filter(value: str, query: str) -> bool:
    return value == query


def not_equals_filter(value: str, query: str) -> bool:
    return value != query


def regex_filter(value: str, query: str) -> bool:
    return re.search(query, value) is not None


def not_regex_filter(value: str, query: str) -> bool:
    return re.search(query, value) is None


def greater_than_filter(value: int, query: int) -> bool:
    return value > query


def greater_than_or_equals_filter(value: int, query: int) -> bool:
    return value >= query


def less_than_filter(value: int, query: int) -> bool:
    return value < query


def less_than_or_equals_filter(value: int, query: int) -> bool:
    return value <= query


ALL_FILTERS: List[Tuple[str, JockeyFilter]] = [
    ("==", equals_filter),
    ("=", equals_filter),
    ("!=", not_equals_filter),
    ("^=", not_equals_filter),
    ("=~", regex_filter),
    ("~=", regex_filter),
    ("!~", not_regex_filter),
    ("^~", not_regex_filter),
    (">", greater_than_filter),
    (">=", greater_than_or_equals_filter),
    ("<", less_than_filter),
    ("<=", less_than_or_equals_filter),
]
ALL_FILTERS = sorted(ALL_FILTERS, key=(lambda x: len(x[0])), reverse=True)


def parse_bool(value: str) -> bool:
    return value.lower() in ['true', 't', 'yes', 'y', '1']


TYPE_PARSERS: Dict[Type[T], Callable[[str], T]] = {
    bool: parse_bool,
}


def get_field_parser(field_type: Type[T]) -> Callable[[str], T]:
    if (parser := TYPE_PARSERS.get(field_type)):
        return parser
    return field_type


def parse_filter(filter_str: str) -> Callable[[Dict[str, Any]], bool]:
    for operator, filter_func in ALL_FILTERS:
        if operator in filter_str:
            field, query = filter_str.split(operator)
            @wraps(filter_func)
            def _filter(obj: Any) -> bool:
                parser = get_field_parser(obj.__annotations__.get(field))
                qval = parser(query)
                # print(f"DEBUG: filtering: func={filter_func}, obj={obj}, field={field}, qval={qval})")
                return filter_func(getattr(obj, field), qval)
            return _filter
    raise ValueError(f"Invalid filter: {filter_str}")


def parse_filters(filter_strs: List[str]) -> List[Callable[[Dict[str, Any]], bool]]:
    return [parse_filter(fstr) for fstr in filter_strs]
