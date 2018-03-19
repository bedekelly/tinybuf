# coding=utf-8
import os

IGNORED_CHARACTERS = "():.-/"


def map_info_from_lines(lines, directory):
    """
    Given some lines and the directory they can be found in,
    return information about a data type.
    """
    user_types = {}
    entries = []

    for line in lines:
        # Check if the line actually contains anything.
        line = line.strip()
        if not line:
            continue

        # Check if the line imports another package.
        if line.startswith("require"):
            _, filename = line.split()
            name = filename.split("/")[-1].replace(".buf", "")
            user_types[name.lower()] = os.path.join(directory, filename)
            continue

        # If not, assume the line defines a property.
        # Strip out any ignored characters like "." and ":".
        for char in IGNORED_CHARACTERS:
            line = line.replace(char, " ")

        # Split the line up into numeric key, key name, and type.
        key, name, *value_type = line.split()

        # Normalize the value's type into lowercase.
        value_type = tuple(v.lower() for v in value_type)

        # Add the data we've found to a list of map entry specifications.
        entries.append((int(key), name, value_type))

    return user_types, entries


def compute_type(value_type, user_types):
    """
    Given a string or list description of a type, choose from
    the builtin types and the user's own types to return a
    corresponding type object.

    This function is recursive to allow for arbitrary nesting
    of higher-order builtin types. For instance, a list of
    optional unsigned ints would be returned as
    List(Optional(UnsignedInt)).
    """

    # Local import necessary to avoid circular dependencies.
    from builtin_types import BUILTINS, HIGHER_ORDER, Map

    # If we've reached the end of a higher-order type,
    # collapse the type down into its actual string.
    if len(value_type) == 1:
        value_type = value_type[0]

    # Make sure our value type is hashable.
    if type(value_type) == list:
        value_type = tuple(value_type)

    # First of all, check if it's an integer, string etc.
    if value_type in BUILTINS:
        return BUILTINS[value_type]

    # Otherwise, see if it's a higher-order type like a list.
    elif type(value_type) == tuple:
        outer_type_name, *inner_type_names = value_type
        outer_type = HIGHER_ORDER[outer_type_name]
        inner_type = compute_type(inner_type_names, user_types)
        return outer_type(inner_type)

    # If not that, it could be a user's own type.
    elif value_type in user_types:
        return Map.from_file(user_types[value_type])

    # If none of those, it's not a type we recognise!
    raise ValueError(f"Type {value_type} not found!")


def make_user_type(type_name, to_bytes):
    """
    Create a user type object with some pre-filled parameters.
    It should be possible to initialize this object with keyword
    parameters.

    :param type_name: The name of the user's type, like Car or Person.
    :param to_bytes: A function to convert the user's type to bytes.
    :return: A user type object.
    """
    class UserType:
        def __init__(self, **records):
            f"""
            Create a new {type_name}.
            """
            self._name = type_name
            self._records = records

            # Allow for attribute access: `car.age` or `person.name`.
            for (k, v) in records.items():
                setattr(self, k, v)

        def to_bytes(self):
            f"""
            Delegate to the outer map's `to_bytes` method to serialize
            this {type_name}.
            """
            return to_bytes(self._records)

        def __eq__(self, other):
            f"""
            Test if this {type_name} is equal to another {type_name}.
            """
            if type(other) == dict:
                return self._records == other
            else:
                return self._records == other._records

        def __str__(self):
            f"""
            Make a pretty string representation of this {type_name}.
            """
            return (
                    f"{self._name}(" +
                    ', '.join(
                        f"{k}={repr(v)}"
                        for (k, v) in self._records.items()
                    ) +
                    ")"
            )

        def __repr__(self):
            f"""
            Delegate to `str` for the `repr` of this {type_name}.
            """
            return str(self)

    return UserType
