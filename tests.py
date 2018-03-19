# coding=utf-8

import os

import pytest

from builtin_types import UnsignedInt, Boolean, String, MapEntrySpec, \
    Map, List, Optional, SignedInt, BuiltinType

# This is a stupendously big number.
from user_types import compute_type

BIG_NUMBER = eval("9" * 100000)


def test_serialize_number():
    """Serialize a multi-byte number."""
    num = 18178
    assert [
        0b1000_0010,
        0b1000_1110,
        0b0000_0001
    ] == list(UnsignedInt.to_bytes(num))


def test_deserialize_number():
    """Deserialize a multi-byte number."""
    bytestring = bytes([
        0b_1010_0001,
        0b_1100_1111,
        0b_1000_0010,
        0b_0100_0001
    ])
    assert 136357793 == UnsignedInt.read(bytestring)


def test_numbers_roundtrip():
    """
    Serialize and deserialize unsigned integers of varying length.
    """
    for num in (0, 1, 2, 178, 300, BIG_NUMBER):
        num2 = UnsignedInt.read(UnsignedInt.to_bytes(num))
        assert num2 == num


def test_text_roundtrip():
    """
    Serialize and deserialize arbitrary unicode text.
    """
    for text in ("", "a", "Hello, world!", "9" * 1000):
        assert text == String.read(String.to_bytes(text))


def test_boolean_roundtrip():
    """
    Serialize and deserialize booleans.
    """
    for b in (True, False):
        assert b == Boolean.read(Boolean.to_bytes(b))


def test_serialize_list():
    """
    Serialize a list of strings.
    """
    assert bytes([
        *UnsignedInt.to_bytes(3),  # Number of values
        *String.to_bytes("Hello, world!"),
        *String.to_bytes("This is the middle value."),
        *String.to_bytes("Goodbye, world!")
    ]) == bytes(List(String).to_bytes([
        "Hello, world!",
        "This is the middle value.",
        "Goodbye, world!",
    ]))


def test_deserialize_list():
    """
    Deserialize a list of unsigned integers.
    """
    input = bytes([
        *UnsignedInt.to_bytes(5),
        *UnsignedInt.to_bytes(1),
        *UnsignedInt.to_bytes(2),
        *UnsignedInt.to_bytes(3),
        *UnsignedInt.to_bytes(4),
        *UnsignedInt.to_bytes(5),
    ])
    assert [1, 2, 3, 4, 5] == List(UnsignedInt).read(input)


def test_roundtrip_list():
    """
    Serialize and deserialize a list of booleans.
    """
    assert [True, False, True, False, True] == (
           List(Boolean).read(
               List(Boolean).to_bytes(
                   [True, False, True, False, True]))
    )


def test_roundtrip_signed_int():
    """
    Serialize and deserialize signed integers.
    """
    for num in (0, -0, -1, 2, -178, 300, -BIG_NUMBER, BIG_NUMBER):
        num2 = SignedInt.read(SignedInt.to_bytes(num))
        assert num2 == num


def test_serialize_optional_boolean():
    """
    Serialize an optional boolean value.
    """
    assert bytes([
        *Boolean.to_bytes(True),
        *Boolean.to_bytes(False)
    ]) == bytes(Optional(Boolean).to_bytes(False))

    assert bytes([
        *Boolean.to_bytes(False)
    ]) == bytes(Optional(Boolean).to_bytes(None))


def test_deserialize_optional_integer():
    """
    Deserialize an optional integer value.
    """
    assert 15 == Optional(UnsignedInt).read(bytes([
        *Boolean.to_bytes(True),
        *UnsignedInt.to_bytes(15)
    ]))
    assert None == Optional(UnsignedInt).read(bytes([
        *Boolean.to_bytes(False)
    ]))


def test_optional_string_roundtrip():
    """
    Serialize and deserialize an optional string value.
    """
    assert "Hello, world!" == Optional(String).read(
        Optional(String).to_bytes("Hello, world!")
    )
    assert None == Optional(String).read(
        Optional(String).to_bytes(None)
    )


def test_deserialize_map():
    """
    Given a bytestream representation of a map – an unordered list
    of numeric key-value pairs – make sure it can be read into a
    dictionary mapping named keys to values.

    This only tests a "shallow" mapping, i.e. it doesn't check
    whether mappings including user-specified types can be
    read.

    It also doesn't test anything to do with the parser: we're
    assuming that we have a complete Mapping object.
    """

    Person = Map(
        MapEntrySpec(1, "name", String),
        MapEntrySpec(2, "age", UnsignedInt),
        MapEntrySpec(3, "likes_chocolate", Boolean)
    )

    bytestream = bytes([
        3,  # Total number of entries.
        1, *String.to_bytes("Bede Kelly"),
        2, *UnsignedInt.to_bytes(20),
        3, *Boolean.to_bytes(True)
    ])

    assert {
        "name": "Bede Kelly",
        "age": 20,
        "likes_chocolate": True
    } == Person.read_as_dict(bytestream)


def test_serialize_map():
    """
    Given a mapping and a dictionary of data, serialize
    a Map into a stream of bytes.
    """
    Car = Map(
        MapEntrySpec(2, "colour", String),
        MapEntrySpec(1, "manufacturer", String),
        MapEntrySpec(3, "preowned", Boolean),
        MapEntrySpec(4, "miles_travelled", UnsignedInt)
    )

    car_data = {
        "preowned": True,
        "manufacturer": "Ford",
        "colour": "brown",
        "miles_travelled": 18562
    }

    assert bytes([
        4,  # Number of entries
        3, *Boolean.to_bytes(True),
        1, *String.to_bytes("Ford"),
        2, *String.to_bytes("brown"),
        4, *UnsignedInt.to_bytes(18562),
    ]) == bytes(
        Car.to_bytes(car_data)
    )


def test_serialize_map_fails_with_missing_values():
    """
    Make sure that if values are missing from the input,
    the Map.to_bytes method complains.
    """
    Paint = Map(
        MapEntrySpec(2, "colour", String)
    )

    with pytest.raises(ValueError):
        bytes(Paint.to_bytes({}))


def test_roundtrip_nested_map():
    """
    Serialize and deserialize a map with nested values.
    """
    Person = Map(
        MapEntrySpec(1, "name", String),
        MapEntrySpec(2, "age", UnsignedInt),
        "Person"
    )
    Family = Map(
        MapEntrySpec(1, "mother", Person),
        MapEntrySpec(2, "father", Person),
        "Family"
    )

    my_family = {
        "mother": {
            "name": "Helen",
            "age": 62
        },
        "father": {
            "name": "Mark",
            "age": 65
        }
    }

    roundtripped_family = Family.read(Family.to_bytes(my_family))
    assert my_family == roundtripped_family


def test_reading_simple_user_map_definition():
    """
    Read a simple Map definition from lines.
    """
    assert Map(
        MapEntrySpec(1, "name", String),
        MapEntrySpec(2, "age", UnsignedInt),
        MapEntrySpec(3, "hair_colour", String)
    ) == Map.from_lines([
        "1. name: string",
        "2 age int",
        "3 :hair_colour (string)"
    ])


def test_reading_user_map_definition_with_list():
    """
    Read a Map definition containing one List key.
    """
    assert Map(
        MapEntrySpec(1, "name", String),
        MapEntrySpec(2, "phones", List(String))
    ) == Map.from_lines([
        "1. name: string",
        "2. phones: list(string)"
    ])


def test_reading_user_map_definition_with_optional():
    """
    Read a Map definition containing one Optional key.
    """
    assert Map(
        MapEntrySpec(1, "name", String),
        MapEntrySpec(2, "maybephone", Optional(String))
    ) == Map.from_lines([
        "1. name: string",
        "2. maybephone: optional(string)"
    ])


def test_reading_user_map_definition_with_list_optional():
    """
    Read a Map definition containing one optional list of values.
    """
    assert Map(
        MapEntrySpec(1, "name", String),
        MapEntrySpec(2, "maybesomephones", Optional(List(String)))
    ) == Map.from_lines([
        "1. name: string",
        "2. maybesomephones: optional(list string)"
    ])


def test_reading_user_map_definition_from_file():
    """
    Read a Map definition from a real file.
    """
    with open("tempfile.buf", "w") as f:
        f.write("""
            1. key : string
            2. bpm : int
        """)

    with open("tempfile.buf") as f:
        assert Map(
            MapEntrySpec(1, "key", String),
            MapEntrySpec(2, "bpm", UnsignedInt)
        ) == Map.from_open_file(f)

    os.remove("tempfile.buf")


def test_reading_nested_user_map_definition_from_file():
    """
    Test a few configurations of loading nested record
    definitions from a file. We're assuming that the
    loading of `Person` works fine as in the above test.
    """
    with open("definitions/Person.buf") as f:
        Person = Map.from_open_file(f)

    expected = Map(
        MapEntrySpec(1, "name", String),
        MapEntrySpec(2, "members", List(Person))
    )

    with open("definitions/Club.buf") as f:
        assert expected == Map.from_open_file(f, "definitions")
    assert expected == Map.from_file("definitions/Club.buf")
    assert expected == Map.from_file("./definitions/Club.buf")


def test_roundtrip_nested_user_defined_nested_map():
    """
    Define a map in a file, and serialize+deserialize some data
    using that map.
    """
    club = {
        "members": [
            dict(name="Bede", age=20),
            dict(name="Jake", age=21),
            dict(name="Cal", age=22)
        ],
        "name": "The Kool Kids Klub"
    }
    Club = Map.from_file("definitions/Club.buf")
    assert club == Club.read(bytes(Club.to_bytes(club)))


def test_convenience_method():
    """
    It should be possible to use `to_bytes` as if it's either a static
    method or an instance method.
    """
    Club = Map.from_file("definitions/Club.buf")

    members = [
        dict(name="Bede", age=20),
        dict(name="Jake", age=21),
        dict(name="Cal", age=22)
    ]

    assert bytes(Club(members=members, name="Klub").to_bytes()) == \
           bytes(Club.to_bytes({"members": members, "name": "Klub"}))


def test_user_type_repr():
    """
    The `str` and `repr` of a user type should be clear and readable.
    """
    Person = Map.from_file("definitions/Person.buf")
    me = Person(name="Bede Kelly", age=20)
    assert "Person(name='Bede Kelly', age=20)" == str(me) == repr(me)


def test_value_error_for_computing_missing_type():
    """
    Computing a missing type should raise a ValueError.
    """
    with pytest.raises(ValueError):
        compute_type("missing_type", {})


def test_map_missing_key_encountered():
    """
    Attempting to read a nonexistent key should raise a KeyError.
    """
    with pytest.raises(KeyError):
        Map().read_key(10, b"")


def test_user_type_attribute_access():
    """
    After creating a user type, it should be possible to access
    attributes of any instance by name.
    """
    Person = Map.from_file("definitions/Person.buf")
    me = Person(name="Bede Kelly", age=20)
    assert 20 == me.age
    assert "Bede Kelly" == me.name


def test_user_type_simple_attributes_with_roundtrip():
    """
    Attributes should be accessible even after a user type has
    been serialized and deserialized.
    """
    Person = Map.from_file("definitions/Person.buf")
    me = Person(name="Bede Kelly", age=20)
    bytestream = me.to_bytes()
    new_me = Person.read(bytestream)
    assert "Bede Kelly" == new_me.name
    assert 20 == new_me.age


def test_separately_created_items():
    """
    Separately-created user types with separate instances should
    still compare equal if their values are equal.
    """
    Person = Map.from_file("definitions/Person.buf")
    Club = Map.from_file("definitions/Club.buf")
    ttonsea = Club(members=[
        Person(name="Bede Kelly", age=20),
        Person(name="Paul Skeggs", age=99)
    ], name="TT-on-Sea")
    assert ttonsea == Club.read(Club(members=[
        Person(name="Bede Kelly", age=20),
        Person(name="Paul Skeggs", age=99)
    ], name="TT-on-Sea").to_bytes())


def test_creating_abstract_class():
    """
    It shouldn't be possible to use an instance of the abstract
    base class BuiltinType.
    """
    with pytest.raises(NotImplementedError):
        BuiltinType().to_bytes(4)

    with pytest.raises(NotImplementedError):
        BuiltinType().read(b"")
