# Adding new provider clases


1. First implement the class and decide on the `provider_class` key. Set the `polymorphic_identity` to that key.

```python

from ._base import Provider


class MyNewProvider(Provider):

    __mapper_args__ = {'polymorphic_identity': 'MY_NEW_PROVIDER'}
```

2. Create a database migration (see e.g. [4085c38e19e8_add_provider_class_rows.py](../../migrations/versions/4085c38e19e8_add_provider_class_rows.py))