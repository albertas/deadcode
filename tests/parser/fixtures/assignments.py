"""Fixture: assignment shapes of every slice-04 form."""

plain = 1
chained = first = second = 2
target_a, target_b = 3, 4
(unpacked_a, unpacked_b) = 5, 6
[list_target_a, list_target_b] = 7, 8
attribute_target.name = 9
subscript_target[0] = 10
deep.attribute_target.deeper[1] = 11

annotated: int = 12
annotated_unparenthesized: int = 13
annotated_no_value: str

augmented = 1
augmented += 2
augmented -= 3
augmented *= 4
augmented /= 5
augmented //= 6
augmented %= 7
augmented **= 8
augmented <<= 9
augmented >>= 10
augmented |= 11
augmented &= 12
augmented ^= 13

deleted = [1, 2]
del deleted[0]
del deleted[1], plain

__all__ = ["plain", "chained"]
__version__ = "1.0"
