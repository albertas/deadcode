from unittest import TestCase

import pytest

from deadcode.data_types import Args
from deadcode.visitor.find_unused_code_visitor import FindUnusedCodeVisitor
from deadcode.visitor.fix_unused_code_visitor import FixUnusedCodeVisitor


class TestConvert1dPartTo2d(TestCase):
    def test_out_of_range_offsets_raise(self):
        # FixUnusedCodeVisitor.__init__ takes a FindUnusedCodeVisitor, not (filenames, args) directly
        find_visitor = FindUnusedCodeVisitor(filenames=[], args=Args())
        visitor = FixUnusedCodeVisitor(find_unused_code_visitor=find_visitor)
        with pytest.raises(ValueError, match='Conversion from 1D to 2D code part failed'):
            # from_char beyond every line -> from_line stays None -> line 184
            visitor.convert_1d_part_to_2d(from_char=100, to_char=200, line_lengths=[5], first_line=1, first_col=0)
