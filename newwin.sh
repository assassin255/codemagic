#!/bin/bash

sudo apt update -y && sudo apt install -y wget gnupg lsb-release software-properties-common
wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh && chmod +x /tmp/llvm.sh && sudo /tmp/llvm.sh 18
sudo apt update -y && sudo apt install -y build-essential clang-18 lld-18 git ninja-build python3-venv python3-pip aria2 libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev libspice-server-dev libspice-protocol-dev llvm-18 llvm-18-dev llvm-18-tools

export PATH="/usr/lib/llvm-18/bin:$PATH"
export CC=clang-18
export CXX=clang++-18
export LD=lld-18

python3 -m venv ~/qemu-env && source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging || true

rm -rf /tmp/qemu-src
git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src
cd /tmp/qemu-src
rm -rf subprojects/berkeley-testfloat-3
mkdir -p build-dir && cd build-dir

EXTRA_CFLAGS="-DDEFAULT_TCG_TB_SIZE=33554432 -DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DTCG_ENABLE_FAST_PREFETCH=1 -DQEMU_STRICT_ALIGN=0 -DTCG_ENABLE_PARALLEL_TB_GEN=1 -DTCG_NO_FAULTING=1 -DQEMU_DISABLE_STRICT_CHECKS=1 -DTCG_ENABLE_EXTENDED_CHAINING=1 -Ofast -ffast-math -march=native -mtune=native -pipe -flto=full -fuse-ld=lld -fno-semantic-interposition -ffp-contract=fast -fno-trapping-math -fno-math-errno -fno-signed-zeros -fno-rounding-math -fno-signaling-nans -freciprocal-math -funroll-loops -finline-functions -finline-limit=1000000 -fmerge-all-constants -fprefetch-loop-arrays -fmodulo-sched -fmodulo-sched-allow-regmoves -faggressive-loop-coalescing -fipa-cp -fpredictive-commoning -falign-functions=32 -falign-loops=32 -falign-jumps=32 -mllvm -polly -mllvm -polly-vectorizer=superword -mllvm -polly-ast-use -mllvm -polly-slp-vectorizer -mllvm -polly-code-gen -mllvm -polly-prevectorize -mllvm -enable-indvars -mllvm -enable-loop-simplify -mllvm -enable-fusion -mllvm -polly-fusion-max -mllvm -polly-opt-fusion -mllvm -polly-intra-scop-simplify -mllvm -enable-loop-interchange -mllvm -polly-run-inliner -funsafe-math-optimizations -mllvm -enable-aggressive-instcombine -mllvm -enable-unsafe-fp-math -fno-finite-math-only -mllvm -enable-newgvn -mllvm -enable-loop-distribute -fwhole-program-vtables -Wno-error -Wno-unused-command-line-argument -Wno-overriding-option"

LDFLAGS="-flto=full -Wl,--lto-O3 -Wl,--icf=all -Wl,--lto-partitions=1 -Wl,--gc-sections -Wl,--plugin-opt=also-emit-llvm"

../configure --prefix=/opt/qemu-optimized --target-list=x86_64-softmmu --enable-tcg --enable-slirp --enable-gtk --enable-sdl --enable-spice --enable-lto --enable-coroutine-pool --enable-mttcg --disable-debug-info --disable-malloc-trim --disable-plugins --disable-docs --disable-werror CC="$CC" CXX="$CXX" LD="$LD" CFLAGS="$EXTRA_CFLAGS" CXXFLAGS="$EXTRA_CFLAGS" LDFLAGS="$LDFLAGS"

ninja -j"$(nproc)" && sudo ninja install

if ! grep -q "/opt/qemu-optimized/bin" ~/.bashrc 2>/dev/null; then echo 'export PATH="/opt/qemu-optimized/bin:$PATH"' >> ~/.bashrc; fi
export PATH="/opt/qemu-optimized/bin:$PATH"
if [ -f ~/.zshrc ]; then echo 'export PATH="/opt/qemu-optimized/bin:$PATH"' >> ~/.zshrc; fi

qemu-system-x86_64 --version
