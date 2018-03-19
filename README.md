# TinyBuf

TinyBuf is a small but capable binary serialization framework.
It allows loading type definitions from files, supports nested
user-specified types, and has higher-order built-in types like
lists and optional values, both of which can be used in
conjunction with user type definitions. 

Although the implementation is proof-of-concept at present, it
does have good test coverage: currently at 100% file coverage
and 100% line coverage.

TinyBuf isn't designed with the same robustness guarantees as
ProtoBuf, and doesn't natively contain version information or
guarantees about the backwards or compatibility of buffers.
For this reason it's likely not suitable for use in production
code.

Currently, the best documentation for TinyBuf is its test cases,
to be found in [tests.py](tests.py).
