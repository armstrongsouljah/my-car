from rest_framework.exceptions import APIException


class CustomValidation(APIException):
    """
    Raise from anywhere to return a structured error response with a custom
    status code.  Default key is "detail" — override with `field` to surface
    field-level validation errors.
    """

    def __init__(self, detail, field="detail", status_code=400):
        self.status_code = status_code
        self.detail = {field: detail}
