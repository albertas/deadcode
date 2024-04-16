# DEP 3 - Removal of unused code might create new unused code
**Status**: Proposed
**Type**: Feature
**Created**: 2024-04-16

## Problem statement
Additional unused code could appear after removal of unused code, since
some code might have been used by code, which was not used.

## Considered solutions
These solutions are possible:
- apply deadcode multiple times till the output does not change in two consequtive runs.
- intelligently mark which code parts are unused and dont mark code as used, if it is used only by the code, which is unused.

## Chosen soluton
Intelligent code tracking should be implemented, to make this algorithm more efficient.
Implementation details should still be considered:
- Code usage tree might have to be constructed with actual links to usages, which might require a lot of memory.
