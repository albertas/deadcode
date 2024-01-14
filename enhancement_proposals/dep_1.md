# DEP 1 - More accurate usage detection
**Status**: Proposed
**Type**: Feature
**Created**: 2024-01-14

## Motivation
Usage detection can be more accurate.
It is common in other unused code detection tools to simply construct
sets of names used in definitions and names used in usage expressions.
And reporting the names, which are in defined set, but not in usage one.

In larger projects cases when names overlap are quite common. In this example:
```
class Foo:
    def validate(self):
        pass

class Bar:
    def validate(self):
        pass

Foo().validate()
```
`validate` name would not be reported if this simple strategy is being used.
However, it is possible to track the types of definitions and usages and
more accurately identify the usages. This DEP 1 proposal specifies the strategy,
which could be used to more accurately track the types of variables.


## Scope construction for definitions:
Dot-separated scope name is being used to identify a scope in each line.

```
# foo.py         # foo
class Bar:       # foo.Bar
    def spam():  # foo.Bar.spam
        pass     # foo.Bar.spam
```

If the `foo.py` file is not on the working path, then its scope is being prefixed with dot separated package names.
For example, if the `foo.py` is in `ham.eggs` package, then the scope of `spam` method will be:
`ham.eggs.foo.Bar.spam`.


## Matching defined type with a type in an expression

Lets say we have a `Bar` type definition and an expression which uses it:

```
# foo.py         # SCOPE
class Bar:       # foo.Bar
    def spam():  # foo.Bar.spam
        pass     # foo.Bar.spam
Bar().spam()     # foo, TYPE: Bar
```

On the expression line `Bar().spam()` the scope is `foo`, the identified type name
is `Bar`. This type `Bar` will be used to search for a type definition (CodeItem instance)
in a namespace `foo` and usages will be marked on it as well as usages of related attributes/methods
will be associated with that type.


## Providing only a part of scope via options is fine
All of these scopes will match the `spam` method:
    `ham.eggs.foo.Bar.spam`
    `foo.Bar.spam`
    `Bar.spam`
    `spam`

The less specific the scope is the more cases it will match,
i.e. `spam` scope would also match a variable named `spam` in any scope as well.
In some sence scopes like `spam`` have wild cards `*.spam` matching any scope prefixes.


## Identifying types of scope parts
When creating the scope parts, each part could also have the type
(e.g. pacakge, module, class, method, variable) associated with it.
When a usage expression is being detected its type could be searched by
using types of scope part, instead of simply comparing scope strings.

For example this code snippet contains two different objects, which could be
matched using a generic `foo.bar` scope:

```
def foo:
    bar = 1

class foo:
    def bar(self):
        pass

foo().bar = 1
```

Deadcode could internally track the type of each scope part and when an expression
is being detected, the defined type could be searched by taking the types of scope parts, not only
the scope string. For example, using a special notation like `>foo%bar` and `#foo>bar`
for scopes could be used for the above example to accurately identify definitions.

User could also provide precise types of scope parts by using a different separator instead of `.`.
These separators could be used for scope part separation:
- `.` - means any type of scope
- `/` - package or module scope
- `#` - class scope
- `>` - function or method scope
- `%` - variable or variable attribute

For example, user could provide this `ham.eggs.foo.Bar.spam` path as well as a more specific one
`ham/eggs/foo#Bar>spam` to exactly match the types of scope parts.


## Type tracking for method arguments and returned values

### Tracking type of arguments
When argument is being passed into a function/method the type remains the same, but the
variable name might change, or it might be put into a container like tuple or dictionary.
Deadcode will attempt to track the types of function/method parameters, however in some cases
the type will be lost and deadcode will fallback to a generic name matching strategy.

In this example:

```
class Foo:
    def bar(self):
        pass

def eggs(ham):
    ham.bar()

spam = Foo()
eggs(spam)
```

Deadcode will be able to accurately detect that type of `ham` is `Foo`.


### Tracking types of returned values
It might be hard to track exact types of variables, for example:

```
clas Eggs:
    pass

class Bar:
    def spam():
        return Eggs()

variable = Bar().spam()
print(variable)
```

Parsing the returned type of `Bar.spam` is complicated.
In some cases, the returned type might only be determined dynamically during a runtime
and it might depend on method's implementation details.
Hence, in some cases the types won't be identified
due to runtime not being available during static code analysis.

The Deadcode policy on this is that when a type is being lost due to inability
to accurately identify it.

In such cases the Deadcode will loose a way to accurately identify the type of variables/attributes.
Hence a generic name matching will be used instead in these cases, just like vulture does.
If more than one definition with the same name is detected the warning should be issues
(if enough verbosity is enabled).
In addition, type hints could be used to try to detect the type more easily in such cases.
