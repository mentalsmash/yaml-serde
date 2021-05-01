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
"""Simplified YAML serialization framework"""

__version__ = "0.4.1"
__license__ = "Apache-2.0"
__status__ = "Prototype"
__author__ = "Andrea Sorbini"
__maintainer__ = "Andrea Sorbini"
__email__ = "dev@mentalsmash.org"
__copyright__ = "Copyright 2020-2021, Andrea Sorbini"
__credits__ = [ "Andrea Sorbini" ]

import types
import pathlib
import collections.abc
from collections import namedtuple
import json as sys_json
import yaml

__all__ = [
  "serialize",
  "yml",
  "json",
  "deserialize",
  "yml_obj",
  "json_obj",
  "repr_yml",
  "repr_py",
  "YamlError",
  "YamlObject",
  "SerializationFormat",
  "YamlSerializationFormat",
  "JsonSerializationFormat",
  "formats",
  "FileSystem",
  "LocalFileSystem",
  "YamlSerializer",
  "YamlDict",
]

################################################################################
# Public serialization functions
################################################################################
def serialize(obj, format, **kwargs):
  """Serialize an object to a string or file.
  
  Conversion to string will be performed using the selected `format` on the
  object returned by `repr_yml(obj, **kwargs)`.

  The resulting string is always returned as output, but it may also be
  saved into a file, using argument `to_file` to specify the path of an
  output file.
  
  The file and any parent directory will be created if they dont't already
  exist. The file's contents will be overwritten, unless `append_to_file=True`
  is specified.

  The object's string representation will be passed to
  `YamlSerializer::file_format_out()` to give custom serializers a chance to
  customize the value stored in the file.

  This can also be achieved using a custom `FileSystem` in the serializer.
  """
  serializer = YamlSerializer.assert_yaml_serializer(
    obj, el_cls=kwargs.get("el_cls"), key_cls=kwargs.get("key_cls"))
  return serializer.to_yaml(obj, format=format, **kwargs)

def yml(obj, **kwargs):
  """Serialize an object to a YAML string or file.
  
  The generated YAML will include the YAML document prefix (`---\n`) and
  suffix (`...\n`), unless `partial=True` is used, in which case both
  prefix and suffix will be omitted.

  This function is just a convenience wrapper to invoke `serialize()` with
  `format="yaml"`.
  """
  return serialize(obj, "yaml", **kwargs)

def json(obj, **kwargs):
  """Serialize an object to a JSON string or file.
  
  This function is just a convenience wrapper to invoke `serialize()` with
  `format="json"`.
  """
  return serialize(obj, "json", **kwargs)

def deserialize(cls, input_str, format, **kwargs):
  """Convert a string or file into a Python object.
  
  Conversion from string to a Python class will be performed by calling
  `repr_py(cls, input_str, **kwargs)` on the object returned by
  the `format`'s `deserialize()` function.

  The input may be a string, or the path of a file, if `from_file=True` is
  specified.

  The file's contents will be read and passed to method
  `YamlSerializer::file_format_in()` for processing before feeding them to
  the selected `format`.
  """
  serializer = YamlSerializer.assert_yaml_serializer(
    cls, el_cls=kwargs.get("el_cls"), key_cls=kwargs.get("key_cls"))
  return serializer.from_yaml(input_str, format=format, **kwargs)

def yml_obj(cls, yml_str, **kwargs):
  """Convert a YAML string or file into a Python object.
  
  This function is a convenience wrapper to invoke `deserialize()` with
  `format="yaml"`.
  """
  return deserialize(cls, yml_str, "yaml", **kwargs)

def json_obj(cls, yml_str, **kwargs):
  """Convert a JSON string or file into a Python object.
  
  This function is a convenience wrapper to invoke `deserialize()` with
  `format="json"`.
  """
  return deserialize(cls, yml_str, "json", **kwargs)

def repr_yml(py_repr, **kwargs):
  """Convert a Python object into its YAML-safe representation.
  
  This function will be called by `serialize()` to convert an input object into
  something that can be fed to `yaml.safe_dump()`. 

  It can also be useful in the implementation of a custom `YamlSerializer`,
  to recursively convert an object's attributes into YAML-safe values.

  For the conversion to occurr, a `YamlSerializer` implementation must have
  been made available as a "nested class" called `_YamlSerializer` on the
  input object's own class object (`py_repr.__class__._YamlSerializer`).
  
  If no custom serializer is available on the input object's class, the
  library will try to detect the input object's type and use a matching
  "built-in" serializer, possibly resorting to an "identity transformation"
  if the object doesn't match any of the available "built-in" serializers.

  Once the appropriate `YamlSerializer` class has been identified, a
  serializer object will be instantiated, and `repr_yml()`
  will invoke `YamlSerializer::repr_yml()`, passing it all its arguments.

  The serializer object will be cached on the input object
  """
  serializer = YamlSerializer.assert_yaml_serializer(
    py_repr, el_cls=kwargs.get("el_cls"), key_cls=kwargs.get("key_cls"))
  return serializer.repr_yml(py_repr, **kwargs)

def repr_py(cls, yml_repr, **kwargs):
  """Convert a YAML-safe representation into a Python object.
  
  This function will be called by `yml_obj()` to convert the "YAML-safe"
  object obtained from `yaml.safe_load()` into an instance of the class
  requested by the user.

  The conversion must be implemented by a custom `YamlSerializer` class
  stored as on the class object (i.e. `cls._YamlSerializer`). In no
  custom serializer will be 

  """
  serializer = YamlSerializer.assert_yaml_serializer(
    cls, el_cls=kwargs.get("el_cls"), key_cls=kwargs.get("key_cls"))
  return serializer.repr_py(yml_repr, **kwargs)

################################################################################
# YamlError
################################################################################
class YamlError(Exception):
  """A generic exception for all errors occurred during YAML operations"""
  def __init__(self, msg):
    self.msg = msg

################################################################################
# YamlObject
################################################################################
def YamlObject(cls, el_cls=None, key_cls=None):
  """A decorator to explicitly enable YAML serialization on a class
  
  It is not necessary to apply this decorator to a class, since any operation
  it performs will also be automatically applied to the class when used by
  any of the YAML serialization functions.
  
  One reason for using this decorator is to potentially improve source code
  readability, and to instantiate serializers when the code is parsed py the
  Python interpreter, rather then opportunistically at runtime.

  Another would be to properly declare the serializer for a container class
  using optional arguments `el_cls` and `key_cls` (for mappings).
  """
  YamlSerializer.assert_yaml_serializer(cls, el_cls=el_cls, key_cls=key_cls)
  return cls

################################################################################
# SerializationFormats
################################################################################
class SerializationFormat:
  def __init__(self, id : str):
    self.id = id
  def serialize(self, obj, partial=False, **kwargs):
    raise NotImplementedError(f"serialize() not implemented by format {self.id}")
  def deserialize(self, input, **kwargs):
    raise NotImplementedError(f"deserialize() not implemented by format {self.id}")
  def __eq__(self, other):
    if isinstance(other, SerializationFormat):
      return self.id == other.id
    return NotImplemented
  def __hash__(self):
    return hash(self.id)

class YamlSerializationFormat(SerializationFormat):
  def __init__(self, id="yaml"):
    super().__init__(id)
    self._fmt_doc_full = "---\n{}\n...\n"
    self._fmt_doc_begin ="---\n{}\n"
    self._fmt_doc_end ="{}\n...\n"
  def yaml_dump(self, obj, partial, **kwargs):
    if kwargs.get("unsafe"):
      return yaml.dump(obj)
    else:
      return yaml.safe_dump(obj)
  def yaml_load(self, input, **kwargs):
    if kwargs.get("unsafe"):
      return yaml.unsafe_load(input)
    else:
      return yaml.safe_load(input)
  def serialize(self, obj, partial=False, **kwargs):
    if not partial:
      fmt_str = "---\n{}\n...\n"
    else:
      fmt_str = "{}"
    yml_str = self.yaml_dump(obj, partial=partial, **kwargs)
    return fmt_str.format(yml_str)
  def deserialize(self, input, **kwargs):
    return self.yaml_load(input, **kwargs)

class JsonSerializationFormat(YamlSerializationFormat):
  def __init__(self, id="json"):
    super().__init__(id)
  def json_dump(self, obj, partial, **kwargs):
    return sys_json.dumps(obj)
  def serialize(self, obj, partial=False, **kwargs):
    return self.json_dump(obj, partial=partial, **kwargs)

class _UserSerializationFormats(set):
  def lookup(self, id : str):
    return next(filter(self, lambda f: fmt.id == id), None)

  def add(self, fmt : SerializationFormat):
    if getatrr(self, fmt.id, None) is None:
      setattr(self, fmt.id, fmt)
      self.add(fmt)

  def remove(self, fmt : SerializationFormat):
    if getatrr(self, fmt.id, None) is not None:
      delattr(self, fmt.id)
      self.remove(fmt)

class _SerializationFormats:
  def __init__(self, user_formats=None):
    self.yaml = YamlSerializationFormat()
    self.json = JsonSerializationFormat()
    self.user = _UserSerializationFormats()
    if user_formats is not None:
      for k, fmt in user_formats.items():
        self.register(k, fmt)

  def register(self, id, fmt_cls):
    if not issubclass(fmt_cls, SerializationFormat):
      raise YamlError(f"class is not a SerializationFormat: {fmt_cls}")
    fmt = getattr(self.user, id, None)
    if fmt is not None:
      if fmt.__class__ != fmt_cls:
        raise YamlError(f"format already registered: {f}")
    else:
      fmt = fmt_cls(id)
      self.user.add(fmt)
    return fmt

  def unregister(self, id):
    fmt = getattr(self.user, id, None)
    if fmt is None:
      raise YamlError(f"format not registered: {id}")
    self.user.remove(fmt)
    return fmt

  def lookup(self, id):
    if id == "yaml":
      return self.yaml
    elif id == "json":
      return self.json
    else:
      return self.user.lookup(id)

"""Serialization formats used by YamlSerializer.

Users can register custom formats using `formats.register(id, fmt_cls)`.
"""
formats = _SerializationFormats()

################################################################################
# FileSystem
################################################################################
class FileSystem:
  def write_file(self, file, contents, append=False, **kwargs):
    raise NotImplementedError("write_file() not implemented")
  
  def read_file(self, file, **kwargs):
    raise NotImplementedError("read_file() not implemented")

  def format_output(self, file, output, **kwargs):
    raise NotImplementedError("format_output() not implemented")
  
  def format_input(self, file, input, **kwargs):
    raise NotImplementedError("format_input() not implemented")


class LocalFileSystem(FileSystem):
  def write_file(self, file, contents, append=False, **kwargs):
    if append:
      f_mode = "a"
    else:
      f_mode = "w"
    
    parent_dir = file.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    with file.open(f_mode) as outfile:
      outfile.write(contents)
  
  def read_file(self, file, **kwargs):
    with file.open("r") as f:
      return f.read()

  def format_output(self, file, output, append=False, **kwargs):
    return output
  
  def format_input(self, file, input, **kwargs):
    return input

################################################################################
# YamlSerializer
################################################################################
class YamlSerializer:
  """Base class for all custom YAML serialization mappings."""

  fs = LocalFileSystem()

  @staticmethod
  def assert_yaml_serializer_class(cls, el_cls=None, key_cls=None):
    serializer_cls = getattr(cls, "_YamlSerializer", None)
    if (serializer_cls is None):
      # If no custom YamlSerializer class was defined for the class, we might be
      # able to use one of the "built-in" serializers, if the class is a
      # container of some kind. These serializers take the target class as an
      # argument to their constructors so that they may be able to instantiate
      # objects of the class from the values obtained from `yaml.safe_load()`.
      # For this reason, any container class should always a "copy constructor"
      # which takes a list of elements to be added to the container upon
      # initialization, e.g. list(a, b, c). All standard Python types support
      # this signature in their constructors, but this might not be the case
      # if `cls` is a user-defined container.
      # If the class is not a container, we will use the base YamlSerializer
      # which implements "identity" conversions. Things are likely NOT going to
      # work, unless the class defines a "copy constructor" which accepts a
      # single named argument `yml_repr`, containing the YAML-safe version.
      serializer_cls = BuiltinYamlSerializerClass(cls, el_cls=el_cls, key_cls=key_cls)
      
      # Try to store the serializer class on the class object for future reuse.
      # This might fail if the target class is a Python built-in type.
      try:
        setattr(cls, "_YamlSerializer", serializer_cls)
      except:
        # Ignore failure, assuming it's because we tried to cache the serializer
        # on a built-in type.
        pass
    
    if not issubclass(serializer_cls, YamlSerializer):
      raise YamlError("invalid YAML serializer for class: {}".format(cls))

    return serializer_cls

  @staticmethod
  def assert_yaml_serializer(obj, el_cls=None, key_cls=None):
    # Check if the object already has a serializer associated to it. This might
    # be the result of a previous call to this function, or a serializer
    # instance that was "monkey-patched" on the object itself.
    serializer = getattr(obj, "_yaml_serializer", None)
    if serializer is None:
      # If the object doesn't have a serializer and it is not a class itself,
      # call this method recursively so that the new serializer will be cached
      # for all instances of the class.
      cached_serializer = None
      if not isinstance(obj, type):
        serializer = YamlSerializer.assert_yaml_serializer(obj.__class__, el_cls=el_cls, key_cls=key_cls)
        # Check if the serializer was cached on the class, other wise try to
        # cache it on the object itself.
        cached_serializer = getattr(obj, "_yaml_serializer", None)
      else:
        # lookup the associated serializer class, and instantiate one.
        # `obj` is a class itself, so use it directly to lookup the serializer.
        serializer_cls = YamlSerializer.assert_yaml_serializer_class(obj, el_cls=el_cls, key_cls=key_cls)
        serializer = serializer_cls()
      # Cache the new serializer on the object. This might fail if the object
      # if "read-only" (e.g. if it's a built-in Python class), so ignore any
      # failure silently, since this is just an optimization.
      if not cached_serializer:
        try:
          setattr(obj, "_yaml_serializer", serializer)
        except:
          pass
    elif not isinstance(serializer, YamlSerializer):
      raise YamlError("invalid YAML serializer for object: {}".format(obj))

    return serializer

  def __init__(self):
    if not isinstance(self.fs, FileSystem):
      raise YamlError("invalid FileSystem for serializer")

  def file_write(self, file, contents, append=False, **kwargs):
    return self.fs.write_file(file, contents, append=append, **kwargs)
  
  def file_read(self, file, **kwargs):
    return self.fs.read_file(file, **kwargs)

  def file_format_out(self, file, yml_str, **kwargs):
    return self.fs.format_output(file, yml_str, **kwargs)
  
  def file_format_in(self, file, yml_str, **kwargs):
    return self.fs.format_input(file, yml_str, **kwargs)
  
  def _file_write(self, file, contents, append=False, **kwargs):
    if not isinstance(file, pathlib.Path):
      file = pathlib.Path(file)
    return self.file_write(file, contents, append=append, **kwargs)
  
  def _file_read(self, file, **kwargs):
    if not isinstance(file, pathlib.Path):
      file = pathlib.Path(file)
    return self.file_read(file, **kwargs)
  
  def _file_format_out(self, file, yml_str, **kwargs):
    if not isinstance(file, pathlib.Path):
      file = pathlib.Path(file)
    return self.file_format_out(file, yml_str, **kwargs)
  
  def _file_format_in(self, file, yml_str, **kwargs):
    if not isinstance(file, pathlib.Path):
      file = pathlib.Path(file)
    return self.file_format_in(file, yml_str, **kwargs)

  def repr_yml(self, py_repr, **kwargs):
    return py_repr
  
  def repr_py(self, yml_repr, **kwargs):
    return yml_repr
  
  def _lookup_format(self, format):
    global formats
    if isinstance(format, str):
      format = formats.lookup(format)
    elif not isinstance(format, SerializationFormat):
      raise YamlError("format must be either a string or a SerializationFormat")
    return format

  def to_yaml(self,
      obj,
      format="yaml",
      to_file=None,
      partial=False,
      append_to_file=False,
      **kwargs):
    format = self._lookup_format(format)

    yaml_repr = self.repr_yml(obj, to_file=to_file, **kwargs)

    yml_str = format.serialize(yaml_repr, partial=partial, **kwargs)

    if to_file is not None:
      file_contents = self._file_format_out(to_file, yml_str, **kwargs)
      self._file_write(to_file, file_contents, append_to_file)
    
    return yml_str

  def from_yaml(self, yml_str, format="yaml", **kwargs):
    format = self._lookup_format(format)

    if kwargs.get("from_file"):
      file = yml_str
      yml_str = self._file_read(file, **kwargs)
      yml_str = self._file_format_in(file, yml_str, **kwargs)

    yml_repr = format.deserialize(yml_str, **kwargs)
    return self.repr_py(yml_repr, **kwargs)

################################################################################
# Built-in YamlSerializers
################################################################################
def BuiltinYamlSerializerClass(cls, el_cls=None, key_cls=None):
  def wrapper_serializer_subclass(parent, c, **kwargs):
    kwargs["_tgt_cls"] = c
    return type(f"{c.__name__}YamlSerializer", (parent,), kwargs)
  if issubclass(cls, collections.abc.Mapping):
    return wrapper_serializer_subclass(
      _MappingYamlSerializer, cls, _el_cls=el_cls, _key_cls=key_cls)
  elif issubclass(cls, collections.abc.Set):
    return wrapper_serializer_subclass(_SetYamlSerializer, cls, _el_cls=el_cls)
  elif issubclass(cls, collections.abc.Collection):
    return wrapper_serializer_subclass(
      _CollectionYamlSerializer, cls, _el_cls=el_cls)
  elif issubclass(cls, collections.abc.Iterable):
    return wrapper_serializer_subclass(
      _IterableYamlSerializer, cls, _el_cls=el_cls)
  else:
    return wrapper_serializer_subclass(_WrapperYamlSerializer, cls)

class _WrapperYamlSerializer(YamlSerializer):
  def __init__(self):
    if not getattr(self, "_tgt_cls", None):
      raise YamlError("invalid wrapper serializer, no target class specified")

  def repr_py(self, yml_repr, **kwargs):
      py_repr = self._tgt_cls(yml_repr=yml_repr)
      return py_repr

class _ContainerYamlSerializer(_WrapperYamlSerializer):
  def __init__(self):
    super().__init__()
    if not getattr(self, "_el_cls", None):
      self._el_cls = None

  def repr_py(self, yml_repr, **kwargs):
    if self._el_cls is None:
      py_repr = self._tgt_cls(yml_repr)
    else:
      py_repr = self._tgt_cls((repr_py(self._el_cls, v, **kwargs) for v in yml_repr))
    return py_repr

class _MappingYamlSerializer(_ContainerYamlSerializer):
  def __init__(self):
    super().__init__()
    if not issubclass(self._tgt_cls, collections.abc.Mapping):
      raise YamlError("serializer's target is not a Mapping")
    if not getattr(self, "_key_cls", None):
      self._key_cls = None
    
  def repr_yml(self, py_repr, **kwargs):
    yml_repr = {repr_yml(k, **kwargs): repr_yml(v, **kwargs) 
                    for k, v in py_repr.items()}
    return yml_repr

  def repr_py(self, yml_repr, **kwargs):
    if self._el_cls is None:
      py_repr = self._tgt_cls(yml_repr)
    elif self._key_cls is None:
      py_repr = self._tgt_cls({k: repr_py(self._el_cls, v, **kwargs)
        for k, v in yml_repr.items()})
    else:
      py_repr = self._tgt_cls(
        {repr_py(self._key_cls, k, **kwargs): repr_py(self._el_cls, v, **kwargs)
          for k, v in yml_repr.items()})
    return py_repr

class _SetYamlSerializer(_ContainerYamlSerializer):
  def __init__(self):
    super().__init__()
    if not issubclass(self._tgt_cls, collections.abc.Set):
      raise YamlError("serializer's target is not a Set")

  def repr_yml(self, py_repr, **kwargs):
    yml_repr = set(repr_yml(el, **kwargs) for el in py_repr)
    return yml_repr

class _IterableYamlSerializer(_ContainerYamlSerializer):
  def __init__(self):
    super().__init__()
    if not issubclass(self._tgt_cls, collections.abc.Iterable):
      raise YamlError("serializer's target is not an Iterable")
    if issubclass(self._tgt_cls, str) and self._el_cls is not None:
      raise YamlError("container element specified for a string class")

  def repr_yml(self, py_repr, **kwargs):
    if isinstance(py_repr, str):
      yml_repr = py_repr
    else:
      yml_repr = tuple(repr_yml(el, **kwargs) for el in py_repr)
    return yml_repr

class _CollectionYamlSerializer(_IterableYamlSerializer):
  def __init__(self):
    super().__init__()
    if not issubclass(self._tgt_cls, collections.abc.Collection):
      raise YamlError("serializer's target is not an Iterable")

################################################################################
# YamlDict
################################################################################
class YamlDict(dict):
  """A YAML-based, custom-validated, dictionary.

  `YamlDict` extends the basic Python `dict` to support the specification of
  a basic "dictionary schema" which may then be used to validate the
  dictionary to make sure that it contains the expected keys.
  """
  def __init__(self, *args, **kwargs):
    dict.__init__(self, **kwargs)
    for a in args:
      self.update(a)
    self.validate()
  
  def validate(self):
    pass

  def _key_validator(self, key, validate_fn, msg=None, **kwargs):
    def _validate_el(el):
      if not validate_fn(el):
          self.invalid_key(key, msg=msg)
    return _validate_el
  
  @staticmethod
  def _validate_str(el, non_empty=True):
    is_none = (not non_empty and el is None)
    if not isinstance(el, str) and not is_none:
      return False
    return not non_empty or is_none or len(el) > 0

  def _key_validator_str(self, key, validate_fn=None, non_empty=True, **kwargs):
    def _validate_str(el):
      return YamlDict._validate_str(el, non_empty)
    if not validate_fn:
      validate_fn = _validate_str
    return self._key_validator(key, validate_fn, **kwargs)

  def set_key_default(self, kwargs, key, default, type=None):
    user_val = kwargs.get(key)
    if user_val is not None:
      key_val = user_val
    else:
      key_val = default
    if type is not None:
      key_val = type(key_val)
    kwargs[key] = key_val

  def invalid_key(self, key, msg="invalid key", err=ValueError):
    raise err(f"{msg}: {key}")

  def get(self, key, default=None):
    canary = object()
    val = dict.get(self, key, canary)
    if val != canary:
      return val
    val = self.assert_key(key, value=canary, _assert=False)
    if val != canary:
      return val
    return default

  def assert_key(self,
      key,
      value=None,
      type=object,
      validate=False,
      validate_fn=None,
      _assert=True,
      **kwargs):
    key_s = key.split(".")
    dict_cur = self
    depth = 0
    canary = object()
    add_key = False
    sub_key = None
    key_value = None
    for k in key_s:
      sub_key = k
      key_value = dict.get(dict_cur, sub_key, canary)
      if key_value == canary:
        # Check that the user doesn't try to assert a nested key
        # before they asserted its parent
        if len(key_s) != (depth + 1):
          msg = f"unmatched paths {key_s[depth+1:]}"
          self.invalid_key(key, msg=msg)
        add_key = True
        break
      # Value was found. Check if we've reached end of iteration
      if len(key_s) == (depth + 1):
        # we're done, nothing to do, but return the value
        continue
      # We have more keys to consume, "check" that the obtained
      # value is a dict() that we can recurse into (use assert(),
      # again, because "internal function" and all...)
      if not isinstance(key_value, dict):
        msg = f"not a dictionary {key_s[:depth+1]} ('{key_value}') (depth={depth})"
        self.invalid_key(key, msg=msg)
      dict_cur = key_value
      depth += 1
    if add_key:
      if value is not None and _assert:
        dict_cur[sub_key] = value
      key_value = value
    if not isinstance(key_value, type) and key_value is not None:
      msg = f"invalid key value [expected={type}, found={key_value.__class__}]"
      self.invalid_key(key, msg=msg, err=TypeError)
    if validate:
      if validate_fn:
        validate_fn(key_value, **kwargs)
      else:
        key_value.validate()
    return key_value

  def assert_key_str(self, key, non_empty=True, validate_fn=None, **kwargs):
    return self.assert_key(key,
      type=str,
      validate_fn=self._key_validator_str(key,
        validate_fn=validate_fn,
        non_empty=non_empty,
        **kwargs),
      **kwargs)

  def assert_key_list(self, key,
      non_empty=True,
      validate_elements=False,
      validate_el=None,
      **kwargs):
    return self.assert_key_collection(key,
      non_empty=non_empty,
      validate_elements=validate_elements,
      validate_el=validate_el,
      **kwargs)
  
  def assert_key_dict(self, key,
      non_empty=True,
      validate_elements=False,
      validate_el=None,
      validate_key=None,
      **kwargs):
    return self.assert_key_collection(key,
      non_empty=non_empty,
      validate_elements=validate_elements,
      validate_el=validate_el,
      validate_key=validate_key,
      enumerate_fn=lambda val: enumerate(val.items()),
      get_el_fn=lambda el: el[1],
      get_key_fn=lambda el: el[0],
      **kwargs)

  def assert_key_collection(self, key,
      non_empty=True,
      validate_elements=False,
      validate_el=None,
      validate_key=None,
      enumerate_fn=enumerate,
      get_el_fn=None,
      get_key_fn=None,
      **kwargs):
    if not get_el_fn:
      get_el_fn = lambda el: el
    if not get_key_fn:
      get_key_fn = lambda el: el
    kwargs["value_type"] = kwargs.get("value_type", dict)
    key_value = self.assert_key(key, **kwargs)
    if non_empty and (key_value is None or len(key_value) == 0):
      self.invalid_key(key, msg="empty collection")
    if validate_el or validate_elements:
      for i, el in enumerate_fn(key_value):
        if validate_elements:
          try:
            get_el_fn(el).validate()
          except Exception as e:
            msg = f"invalid element {i} [{e}]"
            self.invalid_key(key, msg=msg)
        if validate_el and not validate_el(get_el_fn(el)):
          self.invalid_key(key, msg=f"invalid element {i}")
        if validate_key and not validate_key(get_key_fn(el)):
          self.invalid_key(key, msg=f"invalid element key {i}")
