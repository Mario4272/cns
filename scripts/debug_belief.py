
import pytest
import sys

def main():
    print("Running belief tests...")
    with open("debug_belief.log", "w", encoding="utf-8") as f:
        # Redirect stdout/stderr to file
        sys.stdout = f
        sys.stderr = f
        ret = pytest.main(["-vv", "tests/test_belief_revision.py"])
    
    # Restore stdout to print result code
    sys.stdout = sys.__stdout__
    print(f"Tests finished. Exit code: {ret}")

if __name__ == "__main__":
    main()
