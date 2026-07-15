#!/usr/bin/env python
"""Docstring-coverage report for the dace package.

Counts modules, classes and functions/methods carrying a docstring,
per sub-package, using only the standard library (ast) — runs on
Python 3.6 as well as on modern interpreters.

Usage: python tools/doc_coverage.py [package_dir]
"""
import ast
import os
import sys
from collections import defaultdict


def walk(path):
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for name in sorted(filenames):
            if name.endswith('.py'):
                yield os.path.join(dirpath, name)


def stats_for(filename):
    with open(filename, 'rb') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return (0, 0), (0, 0), (0, 0)
    m_total, m_doc = 1, 1 if ast.get_docstring(tree) else 0
    c_total = c_doc = f_total = f_doc = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            c_total += 1
            c_doc += 1 if ast.get_docstring(node) else 0
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            f_total += 1
            f_doc += 1 if ast.get_docstring(node) else 0
    return (m_total, m_doc), (c_total, c_doc), (f_total, f_doc)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'dace'
    per_pkg = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for filename in walk(root):
        if os.sep + 'tests' + os.sep in filename:
            continue
        rel = os.path.relpath(filename, root)
        pkg = rel.split(os.sep)[0] if os.sep in rel else '(root)'
        (mt, md), (ct, cd), (ft, fd) = stats_for(filename)
        agg = per_pkg[pkg]
        agg[0] += mt; agg[1] += md
        agg[2] += ct; agg[3] += cd
        agg[4] += ft; agg[5] += fd

    print('%-24s %12s %12s %14s' % ('package', 'modules', 'classes',
                                    'functions'))
    tot = [0] * 6
    for pkg in sorted(per_pkg):
        a = per_pkg[pkg]
        tot = [t + x for t, x in zip(tot, a)]
        print('%-24s %6d/%-5d %6d/%-5d %7d/%-6d' %
              (pkg, a[1], a[0], a[3], a[2], a[5], a[4]))
    print('%-24s %6d/%-5d %6d/%-5d %7d/%-6d' %
          ('TOTAL (doc/total)', tot[1], tot[0], tot[3], tot[2],
           tot[5], tot[4]))
    covered = tot[1] + tot[3] + tot[5]
    total = tot[0] + tot[2] + tot[4]
    print('coverage: %.1f%%' % (100.0 * covered / total if total else 0))


if __name__ == '__main__':
    main()
