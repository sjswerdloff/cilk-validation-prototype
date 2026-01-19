#!/usr/bin/env python3
"""
Convert Cilk Plus to OpenMP SIMD using tree-sitter for proper AST parsing.

Handles:
1. Array assignments (single and multi-line)
2. Reductions (__sec_reduce_add)
3. Conditionals with vector comparisons (wraps entire if-block)

Usage:
    uv run python scripts/cilk_to_openmp_treesitter.py input.c output.c [--log errors.log]
"""

import re
import sys
import argparse
from pathlib import Path

import tree_sitter_c as tsc
from tree_sitter import Language, Parser

# Initialize parser
C_LANGUAGE = Language(tsc.language())
parser = Parser(C_LANGUAGE)


class TreeSitterCilkConverter:
    def __init__(self, log_file=None):
        self.log_file = log_file
        self.warnings = []
        self.conversions = 0
        self.length_var = 'VLENGTH'

    def log(self, msg):
        self.warnings.append(msg)

    def write_log(self):
        if self.log_file:
            with open(self.log_file, 'w') as f:
                for w in self.warnings:
                    f.write(w + '\n')
                if not self.warnings:
                    f.write('No warnings\n')

    def get_indent(self, source_bytes, node):
        """Get the indentation of a node."""
        line_start = source_bytes.rfind(b'\n', 0, node.start_byte) + 1
        indent_bytes = source_bytes[line_start:node.start_byte]
        # Only keep whitespace
        indent = indent_bytes.decode('utf-8', errors='replace')
        return ''.join(c for c in indent if c in ' \t')

    def replace_vall(self, text):
        """Replace [vALL] and [0:VLENGTH] with [i]."""
        text = re.sub(r'\[vALL\]', '[i]', text)
        text = re.sub(r'\[0:VLENGTH\]', '[i]', text)
        text = re.sub(r'\[\d+:(\w+)\]', '[i]', text)
        return text

    def has_cilk_notation(self, text):
        """Check if text contains Cilk Plus array notation."""
        return bool(re.search(r'\[vALL\]|\[0:VLENGTH\]|\[\d+:\w+\]', text))

    def is_reduction(self, text):
        """Check if text contains __sec_reduce_add."""
        return '__sec_reduce_add' in text

    def convert_reduction(self, text, indent):
        """Convert __sec_reduce_add to OpenMP SIMD reduction."""
        # Match: [type] var = __sec_reduce_add(expr[slice])
        match = re.match(
            r'((?:int|double|float)\s+)?(\w+)\s*=\s*__sec_reduce_add\((.+)\[(vALL|\d+:\w+)\]\)\s*;',
            text.strip()
        )
        if not match:
            return None

        type_decl = match.group(1) or ''
        result_var = match.group(2)
        array_expr = match.group(3)

        result = [
            f'{indent}{type_decl}{result_var} = 0;',
            f'{indent}#pragma omp simd reduction(+:{result_var})',
            f'{indent}for (int i = 0; i < {self.length_var}; i++) {{',
            f'{indent}    {result_var} += {array_expr}[i];',
            f'{indent}}}'
        ]
        self.conversions += 1
        return '\n'.join(result)

    def convert_assignment(self, text, indent):
        """Convert Cilk Plus array assignment to OpenMP SIMD loop."""
        converted = self.replace_vall(text.strip())
        result = [
            f'{indent}#pragma omp simd',
            f'{indent}for (int i = 0; i < {self.length_var}; i++) {{',
            f'{indent}    {converted}',
            f'{indent}}}'
        ]
        self.conversions += 1
        return '\n'.join(result)

    def convert_if_statement(self, source_bytes, node, indent):
        """Convert if statement with Cilk Plus notation - wrap entire block in loop."""
        text = source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='replace')
        converted = self.replace_vall(text)

        # Indent the entire if block
        lines = converted.split('\n')
        indented_lines = [f'    {line}' if line.strip() else line for line in lines]
        indented_block = '\n'.join(indented_lines)

        result = [
            f'{indent}#pragma omp simd',
            f'{indent}for (int i = 0; i < {self.length_var}; i++) {{',
            f'{indented_block}',
            f'{indent}}}'
        ]
        self.conversions += 1
        return '\n'.join(result)

    def process_node(self, source_bytes, node, replacements):
        """Recursively process AST nodes, collecting replacements."""
        text = source_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

        # Check if this node contains Cilk Plus notation
        if not self.has_cilk_notation(text):
            return

        indent = self.get_indent(source_bytes, node)

        # Handle declarations with reductions (int x = __sec_reduce_add(...))
        if node.type == 'declaration' and self.is_reduction(text):
            converted = self.convert_reduction(text, indent)
            if converted:
                replacements.append((node.start_byte, node.end_byte, converted))
                return

        # Handle expression statements (assignments and reductions)
        if node.type == 'expression_statement':
            if self.is_reduction(text):
                converted = self.convert_reduction(text, indent)
                if converted:
                    replacements.append((node.start_byte, node.end_byte, converted))
                    return
            elif '=' in text:
                converted = self.convert_assignment(text, indent)
                if converted:
                    replacements.append((node.start_byte, node.end_byte, converted))
                    return

        # Handle if statements - wrap entire block
        if node.type == 'if_statement':
            converted = self.convert_if_statement(source_bytes, node, indent)
            if converted:
                replacements.append((node.start_byte, node.end_byte, converted))
                return

        # Recurse into children
        for child in node.children:
            self.process_node(source_bytes, child, replacements)

    def convert_file(self, input_path, output_path):
        """Convert a C file using tree-sitter parsing."""
        with open(input_path, 'rb') as f:
            source_bytes = f.read()

        tree = parser.parse(source_bytes)
        replacements = []

        self.process_node(source_bytes, tree.root_node, replacements)

        # Sort replacements by position (reverse order for safe replacement)
        replacements.sort(key=lambda x: x[0], reverse=True)

        # Apply replacements
        result = source_bytes
        for start, end, new_text in replacements:
            result = result[:start] + new_text.encode('utf-8') + result[end:]

        with open(output_path, 'wb') as f:
            f.write(result)

        return self.conversions


def main():
    parser_arg = argparse.ArgumentParser(description='Cilk Plus to OpenMP SIMD (tree-sitter)')
    parser_arg.add_argument('input', help='Input C file')
    parser_arg.add_argument('output', help='Output C file')
    parser_arg.add_argument('--log', default='cilk_convert_ts.log', help='Log file')

    args = parser_arg.parse_args()

    converter = TreeSitterCilkConverter(log_file=args.log)
    count = converter.convert_file(args.input, args.output)
    converter.write_log()

    print(f"Converted {count} Cilk Plus constructs")
    if converter.warnings:
        print(f"Warnings: {len(converter.warnings)} (see {args.log})")


if __name__ == '__main__':
    main()
