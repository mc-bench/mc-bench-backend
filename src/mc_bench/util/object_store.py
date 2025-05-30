"""
Copyright 2024 Hunter Senft-Grupp (huntcsg@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the “Software”), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import ast
import os
from io import BytesIO
from string import Formatter

import minio


class Prototype:
    def __init__(self, kind=None, pattern="", parent=None, children=None):
        self.kind = kind
        self._pattern = pattern
        self.registry = {}
        self.parent = parent
        self.children = children or []
        for child in self.children:
            self.add_child(prototype=child, direct_descendent=True)

    def add_child(self, prototype, direct_descendent=True):
        self.registry[prototype.kind] = prototype
        if direct_descendent:
            prototype.parent = self

        for child in prototype.children:
            self.registry[child.kind] = child
            if self.parent:
                self.parent.add_child(prototype=child, direct_descendent=False)

    @property
    def pattern(self):
        parts = []

        if self.parent:
            parts.append(self.parent.pattern)

        parts.append(self._pattern)
        return "/".join([part.strip("/") for part in parts])

    @property
    def keys(self):
        unduped_keys = [key[1] for key in Formatter().parse(self.pattern) if key[1]]
        found_keys = set()
        deduped_keys = []
        for key in unduped_keys:
            if key not in found_keys:
                deduped_keys.append(key)
                found_keys.add(key)

        return deduped_keys

    def get_path(self, **kwargs):
        return self.pattern.format(**kwargs)

    def materialize(self, **kwargs):
        return PrototypeMaterialization(self, **kwargs)

    def __repr__(self):
        return f"Prototype({self.kind!r}, pattern={self.pattern!r}, children={self.children!r})"

    def __getitem__(self, item_or_items):
        if isinstance(item_or_items, str):
            return self.registry[item_or_items]
        else:
            node = self
            for item in item_or_items:
                node = node.registry[item]

            return node

    def get(self, item_or_items, *more_args):
        if more_args:
            key = (item_or_items, *more_args)
        else:
            key = item_or_items

        return self[key]

    def root(self, **kwargs):
        return self.get_path(**kwargs).split("/", 1)[0]

    def prefix(self, **kwargs):
        return self.get_path(**kwargs).split("/", 1)[1]


class PrototypeMaterialization:
    def __init__(self, prototype, **kwargs):
        self.prototype = prototype
        self.kwargs = kwargs

    @property
    def pattern(self):
        unknown_keys = set(self.prototype.keys) - set(self.kwargs)
        pattern_text = self.prototype.pattern
        for unknown_key in unknown_keys:
            pattern_text = pattern_text.replace(
                f"{{{unknown_key}}}", f"{{{{{unknown_key}}}}}"
            )

        return pattern_text.format(**self.kwargs)

    @property
    def keys(self):
        unknown_keys = set(self.prototype.keys) - set(self.kwargs)
        return list(unknown_keys)

    def get_path(self, **kwargs):
        return self.pattern.format(**kwargs)

    def materialize(self, **kwargs):
        new_kwargs = {**self.kwargs, **kwargs}

        return PrototypeMaterialization(self.prototype, **new_kwargs)

    @property
    def children(self):
        return self.prototype.children

    @property
    def parent(self):
        return self.prototype.parent

    def __repr__(self):
        return f"PrototypeMaterialization({self.prototype}, **{self.kwargs!r})"

    def __getitem__(self, item_or_items):
        if isinstance(item_or_items, str):
            child = self.prototype.registry[item_or_items]
            return PrototypeMaterialization(
                prototype=child,
                **self.kwargs,
            )
        else:
            node = self
            for item in item_or_items:
                if isinstance(node, PrototypeMaterialization):
                    node = node.prototype.registry[item]
                elif isinstance(node, Prototype):
                    node = node.registry[item]

            return PrototypeMaterialization(node, **self.kwargs)

    def get(self, item_or_items, *more_args):
        if more_args:
            key = (item_or_items, *more_args)
        else:
            key = item_or_items

        return self[key]

    def root(self, **kwargs):
        if kwargs:
            return self.get_path(**kwargs).split("/", 1)[0].strip("/")
        else:
            return self.pattern.split("/", 1)[0].strip("/")

    def prefix(self, **kwargs):
        return self.get_path(**kwargs).split("/", 1)[1]


def get_client():
    dsn = os.environ["OBJECT_STORE_DSN"]
    access_key = os.environ["OBJECT_STORE_ACCESS_KEY"]
    secret_key = os.environ["OBJECT_STORE_SECRET_KEY"]
    secure = ast.literal_eval(os.environ.get("OBJECT_STORE_SECURE", "True"))

    client = minio.Minio(
        dsn,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )

    return client


# Download to BytesIO
def get_object_as_bytesio(client, bucket_name, object_name):
    try:
        # Get object data
        data = client.get_object(bucket_name, object_name)
        # Read into BytesIO
        buffer = BytesIO()
        for d in data.stream(32 * 1024):
            buffer.write(d)
        # Reset buffer position to start
        buffer.seek(0)
        return buffer
    finally:
        data.close()
        data.release_conn()


# Download to string
def get_object_as_string(client, bucket_name, object_name):
    try:
        # Get object data
        data = client.get_object(bucket_name, object_name)
        # Read into string
        return data.read().decode("utf-8")
    finally:
        data.close()
        data.release_conn()
