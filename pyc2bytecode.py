# decompyle3 version 3.9.0
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.11.5 (tags/v3.11.5:cce6ba9, Aug 24 2023, 14:31:22) [MSC v.1936 64 bit (AMD64)]
# Source filename: pyc2bytecode.py

import argparse, marshal, os, struct, sys, types
from collections import namedtuple

def convert_to_bytecode(code):
    if isinstance(code, types.CodeType):
        return code
    return marshal.loads(code)


def create_argparser():
    parser = argparse.ArgumentParser(description='Convert .pyc file to .pyo file')
    parser.add_argument('pyc_file', help='The .pyc file to convert')
    parser.add_argument('-o', '--output', help='The output file name')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    return parser


def main():
    parser = create_argparser()
    args = parser.parse_args()
    pyc_file = args.pyc_file
    output_file = args.output
    verbose = args.verbose
    if not os.path.exists(pyc_file):
        print('Error: {} does not exist'.format(pyc_file))
        return
    if verbose:
        print('Converting {} to bytecode'.format(pyc_file))
    with open(pyc_file, 'rb') as f:
        magic = f.read(4)
        moddate = f.read(4)
        if verbose:
            print('Magic: {}'.format(magic))
            print('Moddate: {}'.format(moddate))
        code = marshal.load(f)
        bytecode = convert_to_bytecode(code)
        if output_file is None:
            output_file = os.path.splitext(pyc_file)[0] + '.pyo'
        with open(output_file, 'wb') as fw:
            fw.write(magic)
            fw.write(moddate)
            marshal.dump(bytecode, fw)
            if verbose:
                print('Successfully converted {} to {}'.format(pyc_file, output_file))


if __name__ == '__main__':
    main()
