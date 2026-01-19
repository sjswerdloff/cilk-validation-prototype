/*
 * Simple Cilk Plus test for converter validation
 */

#include <stdio.h>
#include <math.h>
#include "common.h"

#define vALL 0:VLENGTH

int main(void) {
    double input[VLENGTH];
    double output[VLENGTH];
    double intermediate[VLENGTH];
    int flags[VLENGTH];

    for (int i = 0; i < VLENGTH; i++) {
        input[i] = TEST_INPUT[i];
        flags[i] = TEST_FLAGS[i];
    }

    // Pattern A: Array section assignment
    output[vALL] = -log(input[vALL]) * 2.0;

    // Pattern A2: Chained operations
    intermediate[vALL] = exp(-input[vALL]) / (input[vALL] + 0.1);

    // Pattern B: Reductions
    int count = __sec_reduce_add(flags[vALL]);
    double sum = __sec_reduce_add(output[vALL]);
    double sum2 = __sec_reduce_add(intermediate[vALL]);

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
