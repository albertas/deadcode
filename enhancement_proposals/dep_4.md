Internal protocol for Code parts which have to be removed

# Problem
Sometimes code parts have to be removed and these four values could be used to
identify the chunk of code, which has to be removed: (line from, column from, line to, column to).
However, sometimes, additional code has to be added like `pass` statement and these four values are
not sufficient for such change.


# Proposed solution
## Option one
Proposal is to use difflib protocol to identify code changes, which supports four values: insert, delete, replace, equal.
 |      'replace':  a[i1:i2] should be replaced by b[j1:j2]
 |      'delete':   a[i1:i2] should be deleted.
 |                  Note that j1==j2 in this case.
 |      'insert':   b[j1:j2] should be inserted at a[i1:i1].
 |                  Note that i1==i2 in this case.
 |      'equal':    a[i1:i2] == b[j1:j2]


This means, that after detecting unused items, detected code item should use:
1. place of a name
2. place of parent node parts 
As an additional step:
3. generate diff for removal. 

## Option two
It seems that a simple extension to current CodeItem could be used: simply add a way to insert additional information.
    If a removed code part is empty and add is empty - its equal.
    If a removed code part is empty and add is not empty - its insert.
    If a removed code part is not empty and add is empty - its remove/delete.
    If a removed code part is not empty and add is not empty - its replace.

This protocol supports all the needed actions, its easier to incorporate it into the code. And no uneeded wrapping is added in this case.

# Decision
Second option is chosen, which adds ability to insert some code in place of removed code. Indentation is a problem, but its possible to solve it.

Question: should this capability be supported by CodeItem or Part (which is now only a tuple)?


Part tuple was extended to have fith element `insert_code` - which allows to achieve add/replace code action.
This code gets inserted in the begining of merged code part.


# Problem faced during implementation:
If an expression, which had pass added gets removed - pass remains after merging all parts to remove.
Temporal solution is to not insert pass if a symbol before the pass gets removed.

Long term solution is to make removable expression tree, if expression with a pass has to be removed - do not add pass to parts to remove at all.
Merging of parts to remove wont have the pass at all.
