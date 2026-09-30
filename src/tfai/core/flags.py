"""Convert Python keyword options into terraform's single-dash flags."""

from typing import Any


def tf_flags(**opts: Any) -> list[str]:
    """Build terraform flags from keyword options.

    - key `var_file` becomes `-var-file`
    - None is omitted
    - True becomes `-flag`, False becomes `-flag=false`
    - lists/tuples repeat the flag once per item
    - anything else becomes `-flag=value`
    """
    flags: list[str] = []
    for name, value in opts.items():
        flag = "-" + name.replace("_", "-")
        if value is None:
            continue
        if value is True:
            flags.append(flag)
        elif value is False:
            flags.append(f"{flag}=false")
        elif isinstance(value, (list, tuple)):
            flags.extend(f"{flag}={item}" for item in value)
        else:
            flags.append(f"{flag}={value}")
    return flags
