################################################################################
# (C) Copyright 2020-2021 Andrea Sorbini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

from yaml_serde import YamlSerializer, repr_yml, repr_py, yml, yml_obj, BuiltinYamlSerializerClass, YamlObject, _MappingYamlSerializer

import collections

class MyClass:
  def __init__(self, foo):
    self.foo = foo

  def __eq__(self, other):
    if isinstance(other, MyClass):
      return self.foo == other.foo
    return NotImplemented

  def __hash__(self):
    return hash(self.foo)
  
  def __repr__(self):
    return f"MyClass({repr(self.foo)})"
  
  class _YamlSerializer(YamlSerializer):
    def repr_yml(self, py_repr, **kwargs):
      return py_repr.foo
    def repr_py(self, yml_repr, **kwargs):
      return MyClass(yml_repr)

class MyClassOrContainerDeserializer(YamlSerializer):
  def repr_py(self, yml_repr, **kwargs):
    if isinstance(yml_repr, collections.abc.Mapping):
      return {self.repr_py(k): self.repr_py(v) for k, v in yml_repr.items()}
    elif (isinstance(yml_repr, str) or
          not isinstance(yml_repr, collections.abc.Sequence)):
      return MyClass(yml_repr)
    elif kwargs.get("unsafe"):
      return tuple(MyClass(v) for v in yml_repr)
    else:
      return [MyClass(v) for v in yml_repr]

def test_collections():
  """Verify that "built-in" collection types can be serialized to YAML.
  
  yaml_serde should be able to handle instances of the following types
  without requiring an explicit serializer:

  - collections.abc.Mapping
  - collections.abc.Set
  - collections.abc.Collection
  - collections.abc.Iterable
  
  """

  ##############################################################################
  mapping = {
    0: 1,
    MyClass(1): MyClass(2),
    "foo": [0, MyClass(1), "bar"],
  }
  yml_str = yml(mapping)
  assert yml_str == """---
0: 1
1: 2
foo:
- 0
- 1
- bar

...
"""

  MyClassOrContainer = type("MyClassOrList", (),
    dict(_YamlSerializer=MyClassOrContainerDeserializer))

  SerializedType = type("MapSerializedType", (dict,), dict())
  assert issubclass(SerializedType, dict)

  YamlObject(SerializedType, el_cls=MyClassOrContainer, key_cls=MyClassOrContainer)
  assert getattr(SerializedType, "_YamlSerializer", None) is not None
  assert issubclass(SerializedType._YamlSerializer, YamlSerializer)
  assert issubclass(SerializedType._YamlSerializer, _MappingYamlSerializer)
  assert getattr(SerializedType, "_yaml_serializer", None) is not None
  assert isinstance(SerializedType._yaml_serializer, SerializedType._YamlSerializer)
  assert SerializedType._yaml_serializer._el_cls == MyClassOrContainer
  assert SerializedType._yaml_serializer._key_cls == MyClassOrContainer

  parsed = yml_obj(SerializedType, yml_str)
  assert isinstance(parsed, SerializedType)
  assert len(parsed) == 3
  assert MyClass(0) in parsed
  assert parsed[MyClass(0)] == MyClass(1)
  assert MyClass(1) in parsed
  assert parsed[MyClass(1)] == MyClass(2)
  assert MyClass("foo") in parsed
  assert isinstance(parsed[MyClass("foo")], list)
  assert MyClass(0) in parsed[MyClass("foo")]
  assert MyClass(1) in parsed[MyClass("foo")]
  assert MyClass("bar") in parsed[MyClass("foo")]

  ##############################################################################

  mapping = [1, (MyClass(1), MyClass(2)), {MyClass(1) : "bar"}]
  yml_str = yml(mapping)
  assert yml_str == """---
- 1
- - 1
  - 2
- 1: bar

...
"""

  SerializedType = type("ListSerializedType", (list,), dict())
  YamlObject(SerializedType, el_cls=MyClassOrContainer)
  parsed = yml_obj(SerializedType, yml_str)
  assert isinstance(parsed, SerializedType)
  assert len(parsed) == 3
  assert MyClass(1) in parsed
  assert isinstance(parsed[1], list)
  assert MyClass(1) in parsed[1]
  assert MyClass(2) in parsed[1]
  assert isinstance(parsed[2], dict)
  assert MyClass(1) in parsed[2]
  assert parsed[2][MyClass(1)] == MyClass("bar")

  ##############################################################################
  mapping = {1, (MyClass(1), MyClass(2)), (0, MyClass(1), "bar")}
  yml_str = yml(mapping, unsafe=True)
  # This test might fail because a set does not impose a specific order,
  # so test against all permutations
  assert yml_str == """---
!!set
1: null
? !!python/tuple
- 1
- 2
: null
? !!python/tuple
- 0
- 1
- bar
: null

...
""" or yml_str == """---
!!set
? !!python/tuple
- 1
- 2
: null
1: null
? !!python/tuple
- 0
- 1
- bar
: null

...
""" or yml_str == """---
!!set
? !!python/tuple
- 1
- 2
: null
? !!python/tuple
- 0
- 1
- bar
: null
1: null

...
""" or yml_str == """---
!!set
1: null
? !!python/tuple
- 0
- 1
- bar
: null
? !!python/tuple
- 1
- 2
: null

...
""" or yml_str == """---
!!set
? !!python/tuple
- 0
- 1
- bar
: null
1: null
? !!python/tuple
- 1
- 2
: null

...
""" or yml_str == """---
!!set
? !!python/tuple
- 0
- 1
- bar
: null
? !!python/tuple
- 1
- 2
: null
1: null

...
"""

  SerializedType = type("SetSerializedType", (set,), dict())
  YamlObject(SerializedType, el_cls=MyClassOrContainer)
  parsed = yml_obj(SerializedType, yml_str, unsafe=True)
  assert isinstance(parsed, SerializedType)
  assert len(parsed) == 3
  assert MyClass(1) in parsed
  assert (MyClass(1), MyClass(2)) in parsed
  assert (MyClass(0), MyClass(1), MyClass("bar")) in parsed
