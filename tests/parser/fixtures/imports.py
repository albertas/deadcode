"""Fixture: import statements of every slice-04 shape."""

import os
import os.path
import os.path as osp
import sys, math
from collections import OrderedDict
from collections import defaultdict as dd
from . import sibling
from .package import module
from .. import parent
from ...greatgrandparent import deep
from mod import (
    a,
    b as c,
)


def use():
    return os.path.join(
        osp.curdir, sys.argv[0], dd, a, c, module, sibling, deep, OrderedDict, parent
    )
