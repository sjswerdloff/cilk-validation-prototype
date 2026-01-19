# Cilk Plus to OpenMP SIMD Validation Prototype

Validates the conversion pattern from Intel Cilk Plus array notation to portable OpenMP SIMD code.

## Background

Intel Cilk Plus was deprecated in ICC 18.0 (2017) and removed from GCC 8.0 (2018). Codebases using Cilk Plus array notation (like [MCsquare](https://gitlab.com/openmcsquare/MCsquare)) are stuck on legacy compilers.

This prototype validates that converting Cilk Plus array notation to explicit loops with `#pragma omp simd` produces identical numerical results.

## Conversion Pattern

### Cilk Plus Array Notation
```c
#define vALL 0:VLENGTH
output[vALL] = -log(input[vALL]) * 2.0;
count = __sec_reduce_add(flags[vALL]);
```

### OpenMP SIMD Equivalent
```c
#pragma omp simd
for (int i = 0; i < VLENGTH; i++) {
    output[i] = -log(input[i]) * 2.0;
}

int count = 0;
#pragma omp simd reduction(+:count)
for (int i = 0; i < VLENGTH; i++) {
    count += flags[i];
}
```

## Test Strategy

1. **Same hardware comparison (x86_64)**: Compare Cilk Plus (GCC 7) vs OpenMP SIMD (GCC 11) on the same Ubuntu runner
2. **Numerical accuracy**: Verify results match within floating-point tolerance (1e-12)
3. **Performance**: Basic timing comparison

## Local Build

### Cilk Plus (requires GCC 7)
```bash
gcc-7 -fcilkplus -O2 -o cilk_test src/cilk_test.c -lm
```

### OpenMP SIMD (any modern compiler)
```bash
gcc -fopenmp-simd -O2 -o openmp_test src/openmp_simd_test.c -lm
# or
clang -Xpreprocessor -fopenmp-simd -O2 -o openmp_test src/openmp_simd_test.c -lm
```

## CI Status

GitHub Actions runs on `ubuntu-20.04` where GCC 7 is available via apt.

## Related

- [MCsquare](https://gitlab.com/openmcsquare/MCsquare) - Proton therapy Monte Carlo (has Cilk Plus dependency)
- [MCsquare Issue #16](https://gitlab.com/openmcsquare/MCsquare/-/issues/16) - ICC deprecation acknowledged
- [MCsquare Issue #39](https://gitlab.com/openmcsquare/MCsquare/-/issues/39) - ICX migration question (unanswered)

## License

Apache 2.0 (same as MCsquare)
