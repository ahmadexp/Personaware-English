#!/bin/sh
set -eu

project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

if ! command -v nasm >/dev/null 2>&1; then
  echo "nasm is required to build the DOS utilities" >&2
  exit 1
fi

mkdir -p installer/bin
mkdir -p utilities/bin

nasm -f bin installer/dos/pwcopy.asm -o installer/bin/PWCOPY.COM
echo "Built installer/bin/PWCOPY.COM"

nasm -f bin installer/dos/pwimage.asm -o installer/bin/PWIMAGE.COM
echo "Built installer/bin/PWIMAGE.COM"

nasm -f bin utilities/dos/pwphoto.asm -o utilities/bin/PWPHOTO.COM
echo "Built utilities/bin/PWPHOTO.COM"
