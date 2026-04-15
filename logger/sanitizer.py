import copy


def sanitize(data: dict, sensitive_keys: list[str], replacement: str = "***REDACTED***") -> dict:
    """Recursively redact sensitive fields from a dict. Never mutates the original."""
    if not isinstance(data, dict):
        return data

    lower_keys = [k.lower() for k in sensitive_keys]
    result = {}
    for key, value in data.items():
        if any(sk in key.lower() for sk in lower_keys):
            result[key] = replacement
        elif isinstance(value, dict):
            result[key] = sanitize(value, sensitive_keys, replacement)
        elif isinstance(value, list):
            result[key] = [
                sanitize(item, sensitive_keys, replacement) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result
