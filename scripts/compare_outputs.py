#!/usr/bin/env python3
"""Compare Cilk Plus and OpenMP SIMD outputs with tolerance."""

import sys

def parse_output(filename):
    result = {}
    with open(filename) as f:
        for line in f:
            if '=' in line:
                key, val = line.strip().split('=', 1)
                try:
                    result[key] = float(val)
                except ValueError:
                    result[key] = val
    return result

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <cilk_output> <openmp_output>")
        sys.exit(1)

    cilk = parse_output(sys.argv[1])
    openmp = parse_output(sys.argv[2])

    tolerance = 1e-12
    passed = True

    for key in cilk:
        if key not in openmp:
            print(f"MISSING: {key} not in OpenMP output")
            passed = False
            continue

        cv, ov = cilk[key], openmp[key]
        if isinstance(cv, float) and isinstance(ov, float):
            diff = abs(cv - ov)
            rel_diff = diff / max(abs(cv), 1e-15)
            if diff > tolerance:
                print(f"MISMATCH: {key} cilk={cv} openmp={ov} diff={diff:.2e} rel={rel_diff:.2e}")
                passed = False
            else:
                print(f"OK: {key} diff={diff:.2e}")
        elif cv != ov:
            print(f"MISMATCH: {key} cilk={cv} openmp={ov}")
            passed = False
        else:
            print(f"OK: {key} = {cv}")

    if passed:
        print("\nSUCCESS: All values match within tolerance")
        sys.exit(0)
    else:
        print("\nFAILURE: Some values differ beyond tolerance")
        sys.exit(1)

if __name__ == "__main__":
    main()
