# yaml-serde - Simplified YAML object serialization

*yaml_serde* provides a framework for implementing custom conversions of
Python objects to and from the YAML serialization format.

These transformations allow applications to use YAML as a simple way to persist
and share objects.

The framework is built on top of PyYAML (`yaml`), as way to wrap functions
`yaml.safe_dump()` and `yaml.safe_load()` so that they may be used with objects
of any user-defined class.

These functions only accept basic Python objects such as numbers, strings,
arrays, and dictionaries, and they are design to reject any generic "object"
(which must be handled using the "unsafe" versions).

For this reason, *yaml_serde* enables users with a way to implement the logic
required to convert instances of a class between their "Python representation"
(i.e. "normal" Python objects) and an equivalent "YAML representation" which
may be consumed (or produced) by the PyYAML functions.

This representation will typically be a dictionary storing the state of the
object using only "safe" types.

The conversion is implemented by defining a nested "serializer" class,
called `_YamlSerializer` and derived from `yaml_serde.YamlSerializer`.

This class must provide two methods:

- `repr_yml(self, py_repr, **kwargs)`:
  - Take an object in its "Python representation" and return the equivalent
    "YAML representation".

- `repr_py(self, yml_repr, **kwargs)`:
  - Take an object's "YAML representation" and return its
    "Python representation".

Two convenience functions (`repr_yml()` and `repr_py()`) can be used to convert
objects between the two formats.

This is useful to build a "recursive" serializer, which converts and parsers
user-defined and/or "unsafe" nested values:

It is also not necessary to implement both conversions, if only one is needed,
for example Python to YAML:

```py
from yaml_serde import YamlSerializer, repr_yml

class MyClass:
  def __init__(self, foo):
    self.foo = foo
    self.bar = [MyClass(1), MyClass(2), MyClass(3)]
  
  class _YamlSerializer(YamlSerializer):
    def repr_yml(self, py_repr, **kwargs):
      return {
        "foo": py_repr.foo,
        "bar": [repr_yml(c) for c in py_repr.bar]
      }
```

When loading a Python object from YAML, it might be convenient to define a
constructor which can optionally take pre-created values loaded from YAML using
`repr_py()`:

```py
from yaml_serde import YamlSerializer, repr_yml, repr_py

class MyClass:
  def __init__(self, foo, bar=None):
    self.foo = foo
    if bar is None:
      self.bar = [MyClass(1), MyClass(2), MyClass(3)]
    else:
      self.bar = bar
  
  class _YamlSerializer(YamlSerializer):
    def repr_yml(self, py_repr, **kwargs):
      return {
        "foo": py_repr.foo,
        "bar": [repr_yml(c) for c in py_repr.bar]
      }
    def repr_py(self, yml_repr, **kwargs):
      bar = [repr_py(MyClass, c) for c in yml_repr["bar"]]
      return MyClass(yml_repr["foo"], bar)
```
