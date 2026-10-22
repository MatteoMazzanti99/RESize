# Contributing to RESize

Thanks for helping! Some ground rules:

1. **Every calculation lives in `core/`** with a docstring giving formula, units and source,
   plus a unit test with a hand-checked value.
2. **Every calculation has an explanation** in `tutor/explanations.py` (the "Why?" text).
3. **No GUI imports in `core/`.**
4. Run `ruff check .` and `pytest` before opening a pull request.
5. Results that change must be re-validated against the benchmarks in `docs/validation/`.
