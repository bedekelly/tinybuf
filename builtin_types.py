# coding=utf-8
from collections import namedtuple

import os

from user_types import make_user_type


class BuiltinType:
    @staticmethod
    def read(bytestream):
        """Read a value of this type from a bytestream."""
        raise NotImplementedError("read(bytestream)")

    @staticmethod
    def to_bytes(value):
        """Write a value of type type to a bytestream."""
        raise NotImplementedError("to_bytes(value)")


class Boolean:
    @staticmethod
    def read(bytestream):
        return bool(UnsignedInt.read(bytestream))

    @staticmethod
    def to_bytes(boolean):
        yield from UnsignedInt.to_bytes(int(boolean))


class String(BuiltinType):
    @staticmethod
    def to_bytes(text):
        encoded = text.encode("utf-8")
        yield from UnsignedInt.to_bytes(len(encoded))
        yield from encoded

    @staticmethod
    def read_n_bytes(n, bytestream):
        while n:
            yield next(bytestream)
            n -= 1

    @classmethod
    def read(cls, bytestream):
        length = UnsignedInt.read(bytestream)
        return bytes(cls.read_n_bytes(length, bytestream)).decode("utf-8")


class UnsignedInt(BuiltinType):
    @staticmethod
    def to_bytes(n):
        # Check the number is "unsigned" (i.e. non-negative).
        more_to_come = True

        while more_to_come:
            # Read the number's lowest 7 bytes.
            next_byte = n & 0b0111_1111

            # Chop those 7 bytes off the end.
            n >>= 7

            # If there's more data to come, set the most significant bit.
            if n:
                next_byte |= 0b1000_0000

            yield next_byte

            more_to_come = n > 0

    @staticmethod
    def read(bytestream):
        number = 0
        offset = 0

        for byte in bytestream:
            # Check for the continuation bit.
            should_read_more = byte & 0b1000_0000

            # Add this byte's value to our running total.
            number |= (byte & 0b0111_1111) << offset
            offset += 7

            # Stop reading if the continuation bit isn't present.
            if not should_read_more:
                break

        return number


class SignedInt(BuiltinType):
    @staticmethod
    def to_bytes(n):
        yield from Boolean.to_bytes(n >= 0)
        yield from UnsignedInt.to_bytes(abs(n))

    @staticmethod
    def read(bytestream):
        bytestream = iter(bytestream)
        positive = Boolean.read(bytestream)
        value = UnsignedInt.read(bytestream)
        if not positive:
            value *= -1
        return value


class List(BuiltinType):
    def __init__(self, inner_type):
        self.inner_type = inner_type

    def __eq__(self, other):
        return self.inner_type == other.inner_type

    def read(self, bytestream):
        # Make sure our bytestream is single-use only!
        bytestream = iter(bytestream)

        values = []
        length = UnsignedInt.read(bytestream)
        for _ in range(length):
            value = self.inner_type.read(bytestream)
            values.append(value)
        return values

    def to_bytes(self, values):
        yield from UnsignedInt.to_bytes(len(values))
        for value in values:
            yield from self.inner_type.to_bytes(value)


class Optional(BuiltinType):
    def __init__(self, inner_type):
        self.inner_type = inner_type

    def __eq__(self, other):
        return self.inner_type == other.inner_type

    def read(self, bytestream):
        # Make sure our bytestream is single-use only!
        bytestream = iter(bytestream)

        has_value = Boolean.read(bytestream)
        if has_value:
            return self.inner_type.read(bytestream)
        return None

    def to_bytes(self, value):
        if value is None:
            yield from Boolean.to_bytes(False)
            return
        yield from Boolean.to_bytes(True)
        yield from self.inner_type.to_bytes(value)


# A MapKeyValue is a name-value pair retrieved from a map.
# The name is a string, and the value can be anything at all.
MapKeyValue = namedtuple("MapKeyValue", "key value")


# A MapEntrySpec is a specification for an entry in a Map.
# The key is a number, the name is a string exposed to the user,
# and the value_type is either a BuiltinType or a UserType.
MapEntrySpec = namedtuple("EntrySpec", "key name value_type")


class Map(BuiltinType):
    """
    A Map is the equivalent of a Python dictionary, and the building
    block for more complex data types.

    Unlike a Python dictionary though, it takes a `mapping`, which
    specifies exactly what keys it has ahead of time. This makes
    it ideal for defining "Record" types, like an Employee who has
    a name and age.
    """
    def __init__(self, *entry_specs, name="UserType"):
        # Allow for specifying the name as the final positional argument.
        if len(entry_specs) > 0 and type(entry_specs[-1]) == str:
            name = entry_specs[-1]
            entry_specs = entry_specs[:-1]
        self.name = name
        self.entry_specs = tuple(entry_specs)

    def __eq__(self, other):
        return self.entry_specs == other.entry_specs

    def read_as_dict(self, bytestream):
        # Make sure our bytestream is single-use only!
        bytestream = iter(bytestream)

        map_data = {}
        number_entries = UnsignedInt.read(bytestream)

        for _ in range(number_entries):
            key = UnsignedInt.read(bytestream)
            name, value = self.read_key(key, bytestream)
            map_data[name] = value

        return map_data

    def read(self, bytestream):
        return self(**self.read_as_dict(bytestream))

    def read_key(self, key, bytestream):
        """
        Read a value with `key` from the given bytestream.

        Look up the value's type in our `entry_specs`, then
        use that information to delegate to something that knows
        how to read the value in question.
        """
        for entry_spec in self.entry_specs:
            if entry_spec.key == key:
                break
        else:
            raise KeyError(f"No type information about key {key}!")

        # Assume that the entry specification's type knows how to
        # read a value from the bytestream.
        value = entry_spec.value_type.read(bytestream)

        return MapKeyValue(entry_spec.name, value)

    def to_bytes(self, value):
        if type(value) != dict:
            value = value._records

        # Given an entry's name, look up its data type.
        specs_by_name = {spec.name: spec
                         for spec in self.entry_specs}

        seen_keys = set()

        # First, send the number of key-value pairs.
        items = list(value.items())
        yield from UnsignedInt.to_bytes(len(items))

        # Next, send the key for each value, then the value itself.
        for (name, inner_value) in value.items():
            spec = specs_by_name[name]
            yield from UnsignedInt.to_bytes(spec.key)
            yield from spec.value_type.to_bytes(inner_value)
            seen_keys.add(name)

        if seen_keys ^ specs_by_name.keys():
            raise ValueError(
                "One or more necessary parameters were unfilled:",
                seen_keys ^ specs_by_name.keys()
            )

    def __call__(self, **kwargs):
        """
        When the Map type is called, we want it to behave like a class
        being instantiated.

        For instance:
            Car = Map.from_file("...")
            my_car = Car(age=12)
        """
        user_type = make_user_type(self.name, self.to_bytes)
        return user_type(**kwargs)

    @classmethod
    def from_lines(cls, lines, directory=".", type_name=None):
        """
        Read a Map type from a plain-text definition, a base directory
        and an optional name for the Map type itself.
        """
        # This local import prevents a circular dependency.
        from user_types import map_info_from_lines, compute_type

        # Parse the given line information.
        user_types, entries = map_info_from_lines(lines, directory=directory)

        # Compute each entry's type and wrap in a MapEntrySpec.
        entry_specs = [
            MapEntrySpec(key, name, compute_type(value_type, user_types))
            for key, name, value_type in entries
        ]

        # Create and return the Map type.
        return Map(*entry_specs, name=type_name)

    @classmethod
    def from_open_file(cls, open_file, directory=".", name=None):
        """
        Read a Map type definition from an open file object.
        """
        return cls.from_lines(iter(open_file), directory, name)

    @classmethod
    def from_file(cls, filename):
        """
        Read a Map type definition from a filename.
        """
        if not filename.endswith(".buf"):
            filename += ".buf"
        filepath = os.path.dirname(filename)
        name = filename.split("/")[-1].replace(".buf", "").title()
        with open(filename) as f:
            return cls.from_open_file(f, filepath, name)


BUILTINS = {
        "string": String,
        "int": UnsignedInt,
        "sint": SignedInt,
        "bool": Boolean
    }

HIGHER_ORDER = {
    "list": List,
    "optional": Optional
}