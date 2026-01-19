/*
 * OpenMP SIMD portable replacement for Cilk Plus array notation
 * Requires: Any modern compiler with OpenMP support
 *
 * This demonstrates the conversion pattern from Cilk Plus to OpenMP SIMD:
 * - Array notation a[0:N] = expr(b[0:N]) becomes #pragma omp simd + loop
 * - __sec_reduce_add() becomes #pragma omp simd reduction(+:var)
 */

#include <stdio.h>
#include <math.h>
#include <time.h>
#include "common.h"

#define ITERATIONS 100

int main(void) {
    double input[VLENGTH];
    double output[VLENGTH];
    double intermediate[VLENGTH];
    int flags[VLENGTH];

    // Accumulators to prevent optimization
    volatile double acc_sum = 0.0;
    volatile double acc_sum2 = 0.0;
    volatile int acc_count = 0;

    // Initialize from constants
    for (int i = 0; i < VLENGTH; i++) {
        input[i] = TEST_INPUT[i];
        flags[i] = TEST_FLAGS[i];
    }

    clock_t start = clock();

    for (int iter = 0; iter < ITERATIONS; iter++) {
        // Pattern A converted: explicit loop with SIMD hint
        #pragma omp simd
        for (int i = 0; i < VLENGTH; i++) {
            output[i] = -log(input[i]) * 2.0;
        }

        // Pattern A2 converted: chained operations
        #pragma omp simd
        for (int i = 0; i < VLENGTH; i++) {
            intermediate[i] = exp(-input[i]) / (input[i] + 0.1);
        }

        // Pattern B converted: explicit reduction with SIMD
        int count = 0;
        #pragma omp simd reduction(+:count)
        for (int i = 0; i < VLENGTH; i++) {
            count += flags[i];
        }

        double sum = 0.0;
        #pragma omp simd reduction(+:sum)
        for (int i = 0; i < VLENGTH; i++) {
            sum += output[i];
        }

        double sum2 = 0.0;
        #pragma omp simd reduction(+:sum2)
        for (int i = 0; i < VLENGTH; i++) {
            sum2 += intermediate[i];
        }

        // Accumulate to prevent optimization
        acc_sum += sum;
        acc_sum2 += sum2;
        acc_count += count;
    }

    clock_t end = clock();
    double elapsed_ms = (double)(end - start) / CLOCKS_PER_SEC * 1000.0;

    // Timing first
    printf("TIMING_MS=%.3f\n", elapsed_ms);
    printf("ITERATIONS=%d\n", ITERATIONS);

    // Results from last iteration (recompute to get final values)
    #pragma omp simd
    for (int i = 0; i < VLENGTH; i++) {
        output[i] = -log(input[i]) * 2.0;
    }
    #pragma omp simd
    for (int i = 0; i < VLENGTH; i++) {
        intermediate[i] = exp(-input[i]) / (input[i] + 0.1);
    }

    int count = 0;
    #pragma omp simd reduction(+:count)
    for (int i = 0; i < VLENGTH; i++) {
        count += flags[i];
    }

    double sum = 0.0;
    #pragma omp simd reduction(+:sum)
    for (int i = 0; i < VLENGTH; i++) {
        sum += output[i];
    }

    double sum2 = 0.0;
    #pragma omp simd reduction(+:sum2)
    for (int i = 0; i < VLENGTH; i++) {
        sum2 += intermediate[i];
    }

    printf("VLENGTH=%d\n", VLENGTH);
    printf("REDUCTION_COUNT=%d\n", count);
    printf("REDUCTION_SUM=%.15g\n", sum);
    printf("REDUCTION_SUM2=%.15g\n", sum2);

    for (int i = 0; i < VLENGTH; i++) {
        printf("OUTPUT[%d]=%.15g\n", i, output[i]);
    }
    for (int i = 0; i < VLENGTH; i++) {
        printf("INTERMEDIATE[%d]=%.15g\n", i, intermediate[i]);
    }

    return 0;
}
