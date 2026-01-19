#!/usr/bin/env python3
"""
Convert Cilk Plus array notation to OpenMP SIMD.

Patterns handled:
1. array[0:N] = expr(other[0:N]) -> #pragma omp simd + loop
2. __sec_reduce_add(array[0:N]) -> #pragma omp simd reduction + loop
3. Handles vALL macro (0:VLENGTH) used in MCsquare

Usage:
    python cilk_to_openmp.py input.c output.c [--log errors.log]
"""

import re
import sys
import argparse
from pathlib import Path


class CilkConverter:
    def __init__(self, log_file=None):
        self.log_file = log_file
        self.warnings = []
        self.conversions = 0

        # Pattern for array slice notation: name[start:length] or name[vALL]
        # Captures: array_name, slice_content (e.g., "0:VLENGTH" or "vALL")
        self.slice_pattern = r'(\w+)\[((?:\d+:\w+)|(?:vALL))\]'

    def log(self, msg):
        self.warnings.append(msg)

    def write_log(self):
        if self.log_file and self.warnings:
            with open(self.log_file, 'w') as f:
                for w in self.warnings:
                    f.write(w + '\n')
        elif self.log_file:
            # Create empty log file to indicate success
            Path(self.log_file).write_text('')

    def extract_length_var(self, slice_content):
        """Extract the length variable from slice notation."""
        if slice_content == 'vALL':
            return 'VLENGTH'  # MCsquare convention
        if ':' in slice_content:
            parts = slice_content.split(':')
            return parts[1]  # The length part
        return None

    def convert_array_assignment(self, line, indent):
        """
        Convert: array[0:N] = expr(other[0:N])
        To: #pragma omp simd
            for (int i = 0; i < N; i++) {
                array[i] = expr(other[i]);
            }
        """
        # Find all array slices in the line
        slices = re.findall(self.slice_pattern, line)
        if not slices:
            return None

        # Get the length variable (should be same for all slices)
        lengths = set(self.extract_length_var(s[1]) for s in slices)
        if len(lengths) > 1:
            self.log(f"WARNING: Mixed lengths in line: {line.strip()}")
            return None

        length_var = lengths.pop()
        if not length_var:
            self.log(f"WARNING: Could not extract length from: {line.strip()}")
            return None

        # Replace all array[slice] with array[i]
        converted = line
        for array_name, slice_content in slices:
            converted = re.sub(
                rf'\b{re.escape(array_name)}\[{re.escape(slice_content)}\]',
                f'{array_name}[i]',
                converted
            )

        # Build the replacement
        result = [
            f'{indent}#pragma omp simd',
            f'{indent}for (int i = 0; i < {length_var}; i++) {{',
            f'{indent}    {converted.strip()}',
            f'{indent}}}'
        ]

        self.conversions += 1
        return '\n'.join(result)

    def convert_reduction(self, line, indent):
        """
        Convert: type result = __sec_reduce_add(array[0:N])
        To: type result = 0;
            #pragma omp simd reduction(+:result)
            for (int i = 0; i < N; i++) {
                result += array[i];
            }
        """
        # Match: [type] var = __sec_reduce_add(array[slice])
        # Type is optional (variable may already be declared)
        match = re.match(
            r'(\s*)((?:int|double|float)\s+)?(\w+)\s*=\s*__sec_reduce_add\((\w+)\[((?:\d+:\w+)|(?:vALL))\]\)\s*;',
            line
        )
        if not match:
            return None

        type_decl = match.group(2) or ''  # May be empty if var already declared
        result_var = match.group(3)
        array_name = match.group(4)
        slice_content = match.group(5)

        length_var = self.extract_length_var(slice_content)
        if not length_var:
            self.log(f"WARNING: Could not extract length from reduction: {line.strip()}")
            return None

        # Build the replacement
        result = [
            f'{indent}{type_decl}{result_var} = 0;',
            f'{indent}#pragma omp simd reduction(+:{result_var})',
            f'{indent}for (int i = 0; i < {length_var}; i++) {{',
            f'{indent}    {result_var} += {array_name}[i];',
            f'{indent}}}'
        ]

        self.conversions += 1
        return '\n'.join(result)

    def convert_file(self, input_path, output_path):
        """Convert a single file."""
        with open(input_path, 'r') as f:
            lines = f.readlines()

        output_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            indent = re.match(r'^(\s*)', line).group(1)

            # Skip preprocessor directives and comments
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
                output_lines.append(line)
                i += 1
                continue

            # Try reduction conversion first (more specific pattern)
            if '__sec_reduce_add' in line:
                converted = self.convert_reduction(line, indent)
                if converted:
                    output_lines.append(converted + '\n')
                    i += 1
                    continue

            # Try array assignment conversion (but not reductions)
            if re.search(self.slice_pattern, line) and '=' in line and '__sec_reduce_add' not in line and not line.strip().startswith('//'):
                converted = self.convert_array_assignment(line, indent)
                if converted:
                    output_lines.append(converted + '\n')
                    i += 1
                    continue

            # No conversion needed
            output_lines.append(line)
            i += 1

        with open(output_path, 'w') as f:
            f.writelines(output_lines)

        return self.conversions


def main():
    parser = argparse.ArgumentParser(description='Convert Cilk Plus to OpenMP SIMD')
    parser.add_argument('input', help='Input C file with Cilk Plus')
    parser.add_argument('output', help='Output C file with OpenMP SIMD')
    parser.add_argument('--log', default='cilk_convert.log', help='Log file for warnings')

    args = parser.parse_args()

    converter = CilkConverter(log_file=args.log)
    count = converter.convert_file(args.input, args.output)
    converter.write_log()

    print(f"Converted {count} Cilk Plus constructs")
    if converter.warnings:
        print(f"Warnings written to {args.log}")
    else:
        print("No warnings")


if __name__ == '__main__':
    main()
