"""Fixture: literal constants of every slice-04 form."""

integers = [
    0,
    1,
    1234567890,
    0x0,
    0xFF,
    0o777,
    0b1010,
    1_000_000,
    0xFF_FF,
    999999999999999999999999999999999999,
    0xDEADBEEFCAFEF00DBAAD,
]

floats = [0.0, 1.5, 0.5, 1e10, 1e-10, 1_000.000_1, 1e1000, 10_00.5]

complexes = [1j, 3.14j, 1.5e-3j, 0j]

booleans = [True, False]

singularities = [None, ...]

strings = [
    "single",
    "double",
    "",
    "",
    'with "inner"',
    "with 'inner'",
    "tab\tescape",
    "newline\nescape",
    "unicode\u00e9escape",
    "named\N{BULLET}escape",
    "hex\x41escape",
    "octal\101escape",
    r"raw\dpath",
    R"raw\uppercase",
    b"bytes",
    b"byte\tescape",
    rb"raw\dbytes",
    "abc",
    "implicit\nacross\nlines",
    """triple\nquoted""",
    """triple\nsingle""",
    """empty triple""",
]

prefixed = ["unicode prefix", "double"]
