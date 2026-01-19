#ifndef COMMON_H
#define COMMON_H

#define VLENGTH 8  // Match MCsquare's typical SIMD width

// Deterministic test data for reproducibility
static const double TEST_INPUT[VLENGTH] = {
    0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8
};

static const int TEST_FLAGS[VLENGTH] = {
    1, 0, 1, 1, 0, 0, 1, 1
};

#endif
