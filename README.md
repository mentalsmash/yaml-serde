# yaml-serde - Simplified YAML serialization framework

*yaml-serde* provides a framework for implementing custom conversions of
Python objects to and from the YAML serialization format.

These transformations allow applications to use YAML as a simple way to persist
and share objects.

## Python to YAML

After the appropriate serializers have been defined (see [Custom YAML serialization](#custom-yaml-serialization)),
objects can be transformed to a YAML string using function `yml()`:

```py
from yaml_serde import yml

bar = Bar()
yml_str = yml(bar)
assert yml_str == """---
bar:
  - foo: 1
  - foo: 2
  - foo: 3

...
"""
```

The result can also be saved directly into a file by specifying a path
with `to_file`:

```py
yml(bar, to_file="bar.yml")
```

If you prefer, you can also convert object to JSON using function `json()`:

```py
from yaml_serde import yml

bar = Bar()
json_str = json(bar)
assert json_str == '[{"foo": 1}, {"foo": 2}, {"foo": 3}]'
```

## YAML to Python

Given a YAML (or JSON) string, you can build a Python object out of it 
using function `yml_obj()`. This function takes a class object and the
input string, and will return an instance of the class built by its
serializer:

```py
import pathlib
from yaml_serde import yml_obj

with pathlib.Path("bar.yml").open("r") as input:
  bar = yml_obj(Bar, input.read())
```

Since loading YAML from a file is common enough, 
`yml_obj()` offers argument `from_file` to indicate that the input is the path
of a file from which to read the input string:

```py
bar = yml_obj(Bar, "bar.yml", from_file=True)
```

## Custom YAML serialization

The *yaml-serde* framework is built on top of [PyYAML](https://pypi.org/project/PyYAML/),
as way to easily call functions `yaml.safe_dump()` and `yaml.safe_load()` on
objects of any user-defined class.

The PyYAML functions only accept basic Python objects such as numbers, strings,
arrays, and dictionaries, and they are designed to reject any generic "object"
(which must be handled using their "unsafe" counterparts).

For this reason, *yaml_serde* allows users to implement the logic required to
convert instances of their classes into "YAML-safe" representations
compatible with the PyYAML functions.

The conversion is implemented by a nested "serializer" class,
called `_YamlSerializer` and derived from `yaml_serde.YamlSerializer`, which
must be manually defined for every class to convert, and provide two methods:

- `YamlSerializer::repr_yml(self, py_repr, **kwargs)`:
  - Take an object in its "Python representation" and return the equivalent
    "YAML representation".
  - The value returned by this function must be safe to pass to
    `yaml.safe_dump()`.

- `YamlSerializer::repr_py(self, yml_repr, **kwargs)`:
  - Take an object's "YAML representation" and return its
    "Python representation".
  - The value returned by this function should be an instance of the associated
    class.

Implementations are free to map an objects state to YAML however they prefer.

For example, in the case of a trivial class, a simple string might be used:

```py
from yaml_serde import YamlSerializer, repr_yml

class MyClass:
  def __init__(self, foo : str):
    self.foo = foo
  
  class _YamlSerializer(YamlSerializer):
    def repr_yml(self, py_repr, **kwargs):
      return py_repr.foo
    def repr_py(self, yml_repr, **kwargs):
      return MyClass(yml_repr)
```

In most cases, a class will likely map to a dictionary, with entries for each of
its state attributes.

Two convenience functions (`repr_yml()` and `repr_py()`) can be used to
automatically invoke an object's serializer, and convert it between the two
formats. These functions can be useful to build a "recursive" serializer:

```py
from yaml_serde import YamlSerializer, repr_yml, repr_py

class Foo:
  def __init__(self, foo):
    self.foo = foo
  
  class _YamlSerializer(YamlSerializer):
    def repr_yml(self, py_repr, **kwargs):
      return {"foo": py_repr.foo}
    def repr_py(self, yml_repr, **kwargs):
      return Foo(foo=yml_repr["foo"])

class Bar:
  def __init__(self, bar=None):
    if bar is None:
      self.bar = [Foo(1), Foo(2), Foo(3)]
    else:
      self.bar = bar
  
  class _YamlSerializer(YamlSerializer):
    def repr_yml(self, py_repr, **kwargs):
      return [repr_yml(f, **kwargs) for f in py_repr.bar]
    def repr_py(self, yml_repr, **kwargs):
      return Bar(bar=[repr_py(Foo, f) for f in yml_repr])
```

The serializer class will be passed through all the extra keyword
arguments passed to the `yml()` and `yml_obj()` functions.

This can be used to implement optional behavior in the serializer,
for example to exclude certain fields from serialization:

```py
from yaml_serde import YamlSerializer, repr_yml

class MyClassWithPrivateFields:
  def __init__(self, user : str, passwd : str):
    self.user = user
    self.passwd = passwd
  
  class _YamlSerializer(YamlSerializer):
    def repr_yml(self, py_repr, **kwargs):
      yml_repr = {"user": py_repr.user}
      if not kwargs.get("public_only"):
        yml_repr["passwd"] = py_repr.passwd
      return yml_repr
    def repr_py(self, yml_repr, **kwargs):
      return MyClass(yml_repr["user"], yml_repr.get("passwd",""))

def test_my_class_with_private_fields():
  from yaml_serde import yml, yml_obj

  obj = MyClassWithPrivateFields("foo", "bar")

  yml_str = yml(obj)
  assert "passwd: bar" in yml_str

  obj = yml_obj(MyClassWithPrivateFields, yml_str)
  assert obj.passwd == "bar"

  yml_str = yml(obj, public_only=True)
  assert "passwd: bar" not in yml_str

  obj = yml_obj(MyClassWithPrivateFields, yml_str)
  assert obj.passwd == ""
```

Class `YamlSerializer` offers two methods which subclasses can override
to customize the serialization of data in files:

- `YamlSerializer::file_format_out()` is called when a YAML string is
  about to be written to a file. It takes the YAML string
  (along with any extra keyword arguments passed to `yml()`), and it
  must return the actual string that will be written to the file system.

- `YamlSerializer::file_format_in()` is called whenever a YAML string is
  loaded from a file. It take the file's contents (along with any extra
  keywork arguments passed to `yml_obj()`) and it must return the
  string to parse into an object.

These function can be used to pre/post-process the contents of a file,
for example to encode it on serialization, and decoding it when the
value is read back from the file:

```py
from yaml_serde import YamlSerializer, repr_yml

class MyEncodedClass:
  def __init__(self, user : str, passwd : str):
    self.user = user
    self.passwd = passwd
  
  class _YamlSerializer(YamlSerializer):
    def repr_yml(self, py_repr, **kwargs):
      return {"user": py_repr.user, "passwd": py_repr.passwd}
    def repr_py(self, yml_repr, **kwargs):
      return MyClass(yml_repr["user"], yml_repr["passwd"])
    def file_format_in(self, yml_str, **kwargs):
      encoder = kwargs["encoder"]
      return encoder.encode(yml_str)
    def file_format_out(self, yml_str, **kwargs):
      encoder = kwargs["encoder"]
      return encoder.decode(yml_str)

def test_my_encoded_class():
  from yaml_serde import yml, yml_obj
  
  from my_encoder_package import MyEncoder

  obj = MyEncodedClass("foo", "bar")
  
  encoder = MyEncoder()

  yml(obj, to_file="encoded.yml", encoder=encoder)
  
  obj = yml_obj(MyEncodedClass, "encoded.yml", from_file=True, encoder=encoder)

  assert obj.user == "foo"
  assert obj.passwd == "bar"
```

A similar result may also be achieved by having the serializer use a custom
`FileSystem` implementation. By default, any `YamlSerializer` will rely on a
`LocalFileSytem` instance, which provides access to writing and storing files
in the local file system, and does not apply any transformation to file
contents.

Overriding the `FileSystem` class allows the same processing logic to be reused
by multiple `YamlSerializer` classes:

```py
from yaml_serde import LocalFileSystem

class MyEncodedFileSystem(LocalFileSystem):
  def __init__(self):
    self.encoded = MyEncoder()

  def process_output(self, output, append=False, **kwargs):
    return self.encoder.encode(output)
  
  def process_input(self, input, **kwargs):
    return self.encoder.decode(input)

class MyEncodedClass:
  def __init__(self, user : str, passwd : str):
    self.user = user
    self.passwd = passwd
  
  class _YamlSerializer(YamlSerializer):
    fs = MyEncodedFileSystem()
    def repr_yml(self, py_repr, **kwargs):
      return {"user": py_repr.user, "passwd": py_repr.passwd}
    def repr_py(self, yml_repr, **kwargs):
      return MyClass(yml_repr["user"], yml_repr["passwd"])

class MyOtherEncodedClass:
  def __init__(self, foo : str):
    self.foo = foo

  class _YamlSerializer(YamlSerializer):
    fs = MyEncodedFileSystem()
    def repr_yml(self, py_repr, **kwargs):
      return py_repr.foo
    def repr_py(self, yml_repr, **kwargs):
      return MyClass(yml_repr)

```