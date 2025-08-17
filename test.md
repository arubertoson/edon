> 💬 Prompt:

provide a code snippet for a dataclass in python

> 🤖 Response

Certainly! Here’s a simple example of how to use a `dataclass` in Python:

```python
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int
    email: str

# Example usage
p = Person(name="Alice", age=30, email="alice@example.com")
print(p)
```

**Output:**
```
Person(name='Alice', age=30, email='alice@example.com')
```

Let me know if you need a more advanced example!
Token usage: 17 input, 110 output

