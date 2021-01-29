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
__version__ = "0.3.0"

import types
import pathlib
import collections.abc
import json as sys_json

import yaml

__all__ = [
    "yml",
    "yml_obj",
    "repr_yml",
    "repr_py",
    "YamlError",
    "YamlSerializer",
    "YamlDict"
]

def json(obj, **kwargs):
    return yml(obj, _json=True, **kwargs)

def yml(obj, **kwargs):
    serializer = YamlSerializer._class_serializer_assert_obj(obj)
    return serializer.to_yaml(obj, **kwargs)

def yml_obj(cls, yml_str, **kwargs):
    serializer = YamlSerializer._class_serializer_assert(cls)
    return serializer.from_yaml(yml_str, **kwargs)

def repr_yml(py_repr, **kwargs):
    serializer = YamlSerializer._class_serializer_assert_obj(py_repr)
    return serializer.repr_yml(py_repr, **kwargs)

def repr_py(cls, yml_repr, **kwargs):
    serializer = YamlSerializer._class_serializer_assert(cls)
    return serializer.repr_py(yml_repr, **kwargs)

class YamlError(Exception):
    def __init__(self, msg):
        self.msg = msg

def YamlObject(cls):
    """A decorator to explicitly enable YAML serialization on a class"""
    YamlSerializer._class_serializer_assert(cls)
    return cls

class YamlSerializer:

    _class_serializer_attr = "_serializer_yml"
    _class_serializer_name = "_YamlSerializer"

    _obj_serializer_attr = "yaml_serializer"
    
    @staticmethod
    def _class_serializer_assert(cls):
        serializer = getattr(cls, YamlSerializer._class_serializer_attr, None)
        if serializer is None:
            serializer_cls = getattr(cls,
                                    YamlSerializer._class_serializer_name,
                                    None)
            if (serializer_cls is None):
                if issubclass(cls, collections.abc.Mapping):
                    serializer = _MappingYamlSerializer(cls)
                elif issubclass(cls, collections.abc.Set):
                    serializer = _SetYamlSerializer(cls)
                elif issubclass(cls, collections.abc.Collection):
                    serializer = _CollectionYamlSerializer(cls)
                elif issubclass(cls, collections.abc.Iterable):
                    serializer = _IterableYamlSerializer(cls)
                else:
                    serializer = YamlSerializer()
            else:
                serializer = serializer_cls()
            try:
                setattr(cls, YamlSerializer._class_serializer_attr, serializer)
            except:
                # Ignore failure, assuming it's because we tried to cache
                # the serializer on a built-in type
                pass
            
        if not isinstance(serializer, YamlSerializer):
            raise YamlError(
                    "invalid YAML serializer for class: {}".format(cls))
        return serializer
    
    @staticmethod
    def _class_serializer_assert_obj(obj):
        serializer_obj = getattr(obj, YamlSerializer._obj_serializer_attr, None)
        if serializer_obj is None:
            serializer_obj = YamlSerializer._class_serializer_assert(obj.__class__)
        elif not isinstance(serializer_obj, YamlSerializer):
            raise YamlError(
                    "invalid YAML serializer for object: {}".format(obj))
        return serializer_obj

    def _yaml_doc_fmt(self, begin):
        if begin:
            return "---\n{}\n...\n"
        else:
            return "{}"
    
    def _file_format_out(self, yml_str, **kwargs):
        return yml_str
    
    def _file_format_in(self, yml_str, **kwargs):
        return yml_str

    def _file_write(self, file, contents, append):
        if isinstance(file, str):
            file = pathlib.Path(file)
        if append:
            f_mode = "a"
        else:
            f_mode = "w"
        
        parent_dir = file.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        with file.open(f_mode) as outfile:
            outfile.write(contents)
    
    def _file_read(self, file):
        if isinstance(file, str):
            file = pathlib.Path(file)
        with file.open("r") as f:
            return f.read()
    
    def _yaml_load(self, yml_str):
        return yaml.safe_load(yml_str)

    def _yaml_dump(self, yml_repr):
        return yaml.safe_dump(yml_repr)
    
    def _json_dump(self, yml_repr):
        return sys_json.dumps(yml_repr)

    def repr_yml(self, py_repr, **kwargs):
        return py_repr
    
    def repr_py(self, yml_repr, **kwargs):
        return yml_repr

    def to_yaml(self,
                obj,
                to_file=None,
                begin_doc=True,
                append_to_file=False,
                **kwargs):

        yml_str_fmt = self._yaml_doc_fmt(begin_doc)

        yaml_repr = self.repr_yml(obj, to_file=to_file, **kwargs)

        if kwargs.get("_json"):
            yml_str = self._json_dump(yaml_repr)
        else:
            yml_str = yml_str_fmt.format(self._yaml_dump(yaml_repr))

        if to_file is not None:
            file_contents = self._file_format_out(yml_str, **kwargs)
            self._file_write(to_file, file_contents, append_to_file)
        
        return yml_str

    def from_yaml(self,
                  yml_str,
                  **kwargs):
        
        if kwargs.get("from_file"):
            yml_str = self._file_read(yml_str)
            kwargs = {k: v for k,v in kwargs.items() if k != "from_file"}
            yml_str = self._file_format_in(yml_str, **kwargs)

        return self.repr_py(self._yaml_load(yml_str), **kwargs)

class _WrapperYamlSerializer(YamlSerializer):
    def __init__(self, tgt_cls):
        self._tgt_cls = tgt_cls
    
    def _py_new(self, yml_repr):
        return self._tgt_cls(yml_repr)

    def repr_py(self, yml_repr, **kwargs):
        py_repr = self._tgt_cls(yml_repr)
        return py_repr

class _MappingYamlSerializer(_WrapperYamlSerializer):
    def _py_new(self, yml_repr):
        return self._tgt_cls(**yml_repr)

    def repr_yml(self, py_repr, **kwargs):
        yml_repr = {repr_yml(k, **kwargs): repr_yml(v, **kwargs) 
                        for k, v in py_repr.items()}
        return yml_repr

class _SetYamlSerializer(_WrapperYamlSerializer):
    def _py_new(self, yml_repr):
        return self._tgt_cls(*yml_repr)

    def repr_yml(self, py_repr, **kwargs):
        yml_repr = set(repr_yml(el, **kwargs) for el in py_repr)
        return yml_repr

class _IterableYamlSerializer(_WrapperYamlSerializer):
    def _py_new(self, yml_repr):
        return self._tgt_cls(*yml_repr)

    def repr_yml(self, py_repr, **kwargs):
        if isinstance(py_repr, str):
            yml_repr = py_repr
        else:
            yml_repr = list(repr_yml(el, **kwargs) for el in py_repr)
        return yml_repr

class _CollectionYamlSerializer(_IterableYamlSerializer):
    pass


class YamlDict(dict):
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

    def _key_validator_str(self, key, validate_fn=None, non_empty=True,
            **kwargs):
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

    def assert_key(self, key,
            value=None, type=object, validate=False, validate_fn=None,
            _assert=True, **kwargs):
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
            msg = "invalid key value [expected={}, found={}]".format(
                type, key_value.__class__)
            self.invalid_key(key, msg=msg, err=TypeError)
        if validate:
            if validate_fn:
                validate_fn(key_value, **kwargs)
            else:
                key_value.validate()
        return key_value

    def assert_key_str(self, key,
            non_empty=True,
            validate_fn=None,
            **kwargs):
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
