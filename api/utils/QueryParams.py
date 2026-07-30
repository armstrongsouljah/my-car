
from rest_framework import status

from utils import Message
from utils.Exception import CustomValidation


def get_bool(request, key, default_value=None, raise_exception=False):

    value = get(request, key, raise_exception)

    if value is None:
        return default_value

    if value.lower() not in ["true", "false"]:
        return default_value

    return value.lower() == "true"


def get_str(request, key, default_value=None, raise_exception=False):

    value = get(request, key, raise_exception)

    if value is None:
        return default_value

    return value


def get_int(request, key, default_value=None, raise_exception=False):

    value = get(request, key, raise_exception)

    if value is None:
        return default_value

    try:
        return int(value)
    except Exception:
        if raise_exception:
            raise CustomValidation(Message.create(f"{key} value must be a valid integer"), status_code=status.HTTP_400_BAD_REQUEST)

        return default_value


def get_float(request, key, default_value=None, raise_exception=False):
    value = get(request, key, raise_exception)

    if value is None:
        return default_value

    try:
        return float(value)
    except Exception:
        if raise_exception:
            raise CustomValidation(Message.create(f"{key} value must be a valid float"), status_code=status.HTTP_400_BAD_REQUEST)

        return default_value


def get_int_list(request, key, default_value=None, raise_exception=False):
    list = default_value
    source = get_str(request, key, raise_exception=raise_exception)

    if source is None:
        return list

    source = source.rstrip(',')
    list_str = source.split(",")

    try:
        for str in list_str:
            value = int(str)
            list.append(value)
    except:
        if raise_exception:
            raise CustomValidation(Message.create(f"{key} contained an invalid valid float"), status_code=status.HTTP_400_BAD_REQUEST)

        return default_value

    return list


def get_str_list(request, key, default_value=None, raise_exception=False):

    source = get_str(request, key, default_value, raise_exception)

    if source is None or source == '':
        return default_value

    source = source.rstrip(',')
    list = source.split(",")

    return list


def get_enum(request, key, options, default_value=None, raise_exception=False):

    value = get(request, key, raise_exception)

    if value not in options:
        if raise_exception:
            raise CustomValidation(Message.create(f"Invalid value {value}, must be one of {options}"))

        return default_value

    return value


def get(request, key, raise_exception=False):

    if key not in request.query_params:

        if raise_exception:
            raise_not_found_exception(key)

        return None

    return request.query_params.get(key)


def get_meta(request, key):
    return request.META.get(key, '')


def raise_not_found_exception(key):
    raise CustomValidation(Message.create(f"{key} not found"), status_code=status.HTTP_404_NOT_FOUND)
