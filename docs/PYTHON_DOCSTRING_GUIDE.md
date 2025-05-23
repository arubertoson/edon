## Style Guide: Docstrings & Inline Comments

**Core Philosophy:**
Your primary goal when generating docstrings is to explain the **"why"** (purpose, rationale) and the **"what"** (high-level behavior, responsibilities) of a code element. Avoid simply rephrasing what's already obvious from the code's signature or name. For inline comments, your goal is to explain the **"why"** of specific implementation details or non-obvious logic.

---

### 5. Docstrings

**General Mandate:**
All **public** modules, functions, classes, and methods **MUST** have a docstring, unless explicitly exempted below.

**A. Universal Docstring Structure (for Modules, Functions, Classes, Methods):**

1.  **Summary Line:**
    * **Content:** A single, concise line summarizing the element's core purpose or objective (the "why").
    * **Brevity:** Must be one line only.
    * **No Redundancy:**
        * MUST NOT merely repeat or rephrase the function/method signature (name, parameters, return type).
        * MUST NOT repeat the class name for a class docstring.
    * **Example of what to avoid:**
        * `def get_user_name(user_id: int) -> str:`
        * *Bad summary:* `Gets the user name for a given user ID.` (Repeats signature)
        * *Good summary:* `Retrieves the persisted full name of a user.` (Explains purpose/action)

2.  **Blank Line:** A single blank line MUST follow the summary line if there is further explanation.

3.  **Detailed Explanation (Optional but Encouraged for Complexity):**
    * **Content:** If the summary line isn't sufficient, provide a more detailed explanation. Focus on:
        * The problem the code solves or the specific goal it achieves.
        * High-level behavior and any critical interactions.
        * Important assumptions or constraints.
    * **NO `Args`/`Returns`/`Raises` Sections:**
        * You MUST NOT include sections like `Args:`, `Parameters:`, `Returns:`, `Yields:`, `Raises:`, `Attributes:`, etc.
        * Type information is in the signature. The docstring's role is to explain the *purpose* and *behavior*, not to duplicate type hints or parameter names in a list format.
        * If a parameter or return value has a non-obvious *meaning* or role crucial to understanding the function's purpose, explain that *narratively* within the detailed explanation, not as a list item.

**B. Module Docstrings:**

* **Purpose:** MUST describe the module's overall purpose, its responsibilities, and what kind of functionality it groups together.
* **Content Example:** "Manages user authentication and session lifecycle." or "Provides utility functions for data serialization and deserialization."

**C. Function/Method Docstrings:**

* **Focus on "Why" and "What":**
    * Clearly explain the function/method's **purpose** (why it exists).
    * Describe its **high-level behavior** (what it aims to accomplish).
* **Avoid Redundancy with Signature:**
    * DO NOT repeat type information from the signature.
    * DO NOT simply rephrase the function name or its parameters.
    * A docstring for a function or method **MAY BE OMITTED IF AND ONLY IF** all of the following conditions are met:
* **Content-Based Necessity (When to OMIT a function/method docstring):**
        1.  Its name is exceptionally clear and self-descriptive (e.g., `get_current_timestamp`).
        2.  Its type signature is present and fully describes the inputs and outputs.
        3.  Its *entire purpose and behavior* are unequivocally obvious from its name and signature alone, leaving no room for ambiguity.
        4.  The docstring would *only* reiterate information already perfectly conveyed by the name and signature.
    * **Example of when to omit:**
        ```python
        class DataProcessor:
            def __init__(self, data: List[int]):
                self._data = data

            def get_data(self) -> List[int]: # Docstring MAY BE OMITTED
                return self._data
        ```
    * **If a docstring is present, it MUST add value beyond the signature.** A redundant docstring (e.g., `"""Gets the data."""` for the example above) is incorrect and should be omitted.

**D. Class Docstrings:**

* **Summary:** Provide a clear, high-level understanding of the class's **role and responsibilities** within the system.
* **Avoid Member Lists:** DO NOT include extensive lists of public attributes or methods if these are self-documenting through their own well-chosen names, type hints, and (if necessary) their own docstrings. Focus on the class's overall purpose.
* **Usage Examples:** Detailed examples of usage are generally better placed in module-level docstrings or separate usage documentation. Only include a very concise example if it's critical to understanding the class's primary purpose.
* **Subclassing Interface:** If the class is designed for subclassing and offers a distinct interface for subclasses (e.g., abstract methods to be implemented, hooks), this specific interface and its purpose SHOULD be described.

**E. Specific Method Docstring Rules:**

* **`__init__` Methods:**
    * MUST NOT have their own docstring.
    * The purpose of `__init__` is to initialize an instance of the class. This is implied by the class itself.
    * Parameters of `__init__` that establish the public state or configuration of the instance should be explained in the *class-level docstring* if their role is not obvious from their names and types.
* **`@property` Accessors (Getter, Setter, Deleter):**
    * **Getter:** A docstring MAY BE OMITTED if its logic is trivial (e.g., `return self._foo`) AND its purpose is clear from the property's name and type hint. If present, it should explain the *meaning* or *source* of the property if not obvious.
    * **Setter/Deleter:** If their logic is non-trivial (e.g., involves validation, side effects, computation), they MUST have a docstring explaining this logic and its purpose. If they are trivial (e.g., simple assignment or deletion with no side effects), the docstring MAY BE OMITTED if their function is obvious.
    * **Redundancy:** A docstring for a simple accessor that only reiterates the obvious (e.g., `"""Gets the foo."""`) MUST be omitted.
* **Private Methods/Functions (e.g., `_private_method`):**
    * **General Rule:** DO NOT require docstrings. Prefer inline comments to explain complex logic within them.
    * **Exception:** If a private method/function is particularly complex, long, or its purpose is not immediately obvious from its name and the surrounding code context, a concise docstring explaining its "why" and "what" (from an internal perspective) IS ENCOURAGED. This docstring follows the general structure but is aimed at maintainers.

**F. References in Docstrings:**

* **Minimize Direct Naming:** Try to reduce direct, fully qualified references to other classes and functions (e.g., ``See :class:`my_module.MyClass```) *within the narrative*.
* **Focus on Concepts:** Instead, explain interactions conceptually if necessary for understanding the current element's purpose. Only use direct references if they are essential for clarity and cannot be conveyed by context or conceptual explanation.
* **Example:**
    * *Avoid:* "This function calls `other_module.process_data()` to prepare the data."
    * *Prefer:* "Prepares the data by leveraging the standard data processing pipeline." (If `other_module.process_data` *is* that pipeline). Or, if more detail is truly needed: "Transforms the input by first normalizing it and then applying a filtering step."

---

### 6. Comments (Inline)

**Core Purpose:** Inline comments explain the **"why"** behind specific implementation choices, algorithms, or non-obvious lines of code. They are for maintainers of the code, including your future self (and other LLMs).

* **Clarity of Intent and Rationale:**
    * USE comments to explain the reasoning behind non-obvious design decisions.
    * USE comments to clarify complex algorithms or tricky logic.
    * USE comments to explain *why* a particular implementation approach was chosen over alternatives, if relevant.
* **Contextual Background:**
    * PROVIDE comments that offer background or context not immediately apparent from reading the code itself (e.g., "Workaround for library bug X," "Optimization based on typical data distribution").
* **High-Level Overviews for Complex Blocks:**
    * For intricate functions or multi-step logical blocks (even within private methods), a brief comment at the beginning of the block summarizing the strategy or steps can be very helpful.
* **AVOID Redundancy (Comments that State the Obvious):**
    * DO NOT comment on what is already perfectly clear from well-written, idiomatic code.
    * **Example of what to avoid:**
        ```python
        count = 0 # Initialize count to zero
        count += 1 # Increment count
        ```
* **Maintain Accuracy:**
    * Comments MUST be kept meticulously up-to-date with the code.
    * An outdated or incorrect comment is significantly worse than no comment. If the code changes, review and update associated comments immediately.
* **Placement:**
    * Place comments on the line immediately preceding the code they describe, or for very short comments, at the end of the line of code they pertain to (after two spaces).

---

**Final Adherence Note:**
When generating or modifying code, strictly adhere to these guidelines for docstrings and comments. If an existing docstring or comment violates these rules (e.g., is redundant, has `Args:` sections), you should correct it or flag it for removal/correction based on these principles. Your output will be evaluated based on adherence to these documentation standards.
