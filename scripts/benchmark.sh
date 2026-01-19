#!/bin/bash
# Benchmark Cilk Plus vs OpenMP SIMD performance

ITERATIONS=${1:-100}

echo "=== Performance Comparison ($ITERATIONS iterations) ==="

echo "Cilk Plus (GCC 7):"
time for i in $(seq 1 $ITERATIONS); do ./cilk_test > /dev/null; done

echo ""
echo "OpenMP SIMD (GCC 11):"
time for i in $(seq 1 $ITERATIONS); do ./openmp_test > /dev/null; done
