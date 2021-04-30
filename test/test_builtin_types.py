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

from yaml_serde import YamlSerializer, repr_yml, repr_py, yml

def test_collections():
  """Verify that "built-in" collection types can be serialized to YAML.
  
  yaml_serde should be able to handle instances of the following types
  without requiring an explicit serializer:

  - collections.abc.Mapping
  - collections.abc.Set
  - collections.abc.Collection
  - collections.abc.Iterable
  
  """

  class MyClass:
    def __init__(self, foo):
      self.foo = foo

    def __eq__(self, other):
      if isinstance(other, MyClass):
        return self.foo == other.foo
      return NotImplemented

    def __hash__(self):
      return hash(self.foo)
    
    class _YamlSerializer(YamlSerializer):
      def repr_yml(self, py_repr, **kwargs):
        return py_repr.foo
      def repr_py(self, yml_repr, **kwargs):
        return MyClass(yml_repr)

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

  mapping = [1, (MyClass(1), MyClass(2)), {MyClass(1) : "bar"}]
  yml_str = yml(mapping)
  assert yml_str == """---
- 1
- - 1
  - 2
- 1: bar

...
"""

  mapping = {1, (MyClass(1), MyClass(2)), (0, MyClass(1), "bar")}
  yml_str = yml(mapping)
  assert yml_str == """---
!!set
1: null
? - 1
  - 2
: null
? - 0
  - 1
  - bar
: null

...
"""
