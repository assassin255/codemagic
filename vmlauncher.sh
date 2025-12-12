#!/usr/bin/env bash
set -e

sudo apt update -y
sudo apt install -y wget gnupg lsb-release software-properties-common build-essential ninja-build git python3 python3-venv python3-pip libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev libspice-server-dev libspice-protocol-dev pkg-config meson

wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add -
sudo add-apt-repository "deb http://apt.llvm.org/jammy/ llvm-toolchain-jammy-21 main"
sudo apt update
sudo apt install -y clang-21 lld-21 llvm-21 llvm-21-dev llvm-21-tools

export PATH="/usr/lib/llvm-21/bin:$PATH"
export CC=clang-21
export CXX=clang++-21
export LD=lld-21

python3 -m venv ~/qemu-env
source ~/qemu-env/bin/activate
pip install --upgrade pip tomli markdown packaging

rm -rf /tmp/qemu-src /tmp/qemu-build
cd /tmp
git clone --depth 1 --branch v10.2.0-rc3 https://gitlab.com/qemu-project/qemu.git qemu-src
mkdir /tmp/qemu-build
cd /tmp/qemu-build

EXTRA_CFLAGS="-DDEFAULT_TCG_TB_SIZE=1048576 -DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DTCG_ENABLE_FAST_PREFETCH=1 -DQEMU_STRICT_ALIGN=0 -DTCG_TARGET_HAS_direct_jump=1 -DTCG_TARGET_HAS_JUMP_CACHE=1 -Ofast -ffast-math -march=native -mtune=native -pipe -flto=full -fuse-ld=lld -fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables -fno-unwind-tables -fno-stack-protector -fno-plt -fno-pic -fno-pie -fno-common -ffp-contract=fast -fno-trapping-math -fno-math-errno -fno-signed-zeros -fno-rounding-math -fno-signaling-nans -funroll-loops -finline-functions -finline-limit=1000000 -fmerge-all-constants -fvectorize -fprefetch-loop-arrays -fmodulo-sched -fmodulo-sched-allow-regmoves -faggressive-loop-coalescing -fipa-cp -fpredictive-commoning -falign-functions=32 -falign-loops=32 -falign-jumps=32"

LDFLAGS="-flto=full -Wl,--lto-O3 -Wl,--icf=all -Wl,--lto-partitions=1 -Wl,--gc-sections"

../qemu-src/configure --prefix=/opt/qemu-optimized --target-list=x86_64-softmmu --enable-tcg --enable-slirp --enable-gtk --enable-sdl --enable-spice --enable-lto --enable-coroutine-pool --disable-debug-info --disable-malloc-trim --disable-plugins --disable-docs --disable-werror --disable-fdt CC="$CC" CXX="$CXX" LD="$LD" CFLAGS="$EXTRA_CFLAGS" CXXFLAGS="$EXTRA_CFLAGS" LDFLAGS="$LDFLAGS"

ninja -j"$(nproc)"
sudo ninja install

if ! grep -q "/opt/qemu-optimized/bin" ~/.bashrc 2>/dev/null; then
    echo 'export PATH="/opt/qemu-optimized/bin:$PATH"' >> ~/.bashrc
fi
export PATH="/opt/qemu-optimized/bin:$PATH"
if [ -f ~/.zshrc ]; then
    echo 'export PATH="/opt/qemu-optimized/bin:$PATH"' >> ~/.zshrc
fi

qemu-system-x86_64 --version
echo "LLVM-21 + QEMU 10.2.0-rc3 TCG optimized build done"
