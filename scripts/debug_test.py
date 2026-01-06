
import sys

import pytest


def main():
    print("Running tests...")
    with open("debug_test.log", "w", encoding="utf-8") as f:
        # Redirect stdout/stderr
        sys.stdout = f
        sys.stderr = f
        ret = pytest.main(["-vv", "-l", "tests/test_vector_lifecycle.py"])
    print(f"Done. Ret: {ret}")

if __name__ == "__main__":
    main()
