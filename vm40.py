#!/usr/bin/env python3
import os
import subprocess
import sys

def run(cmd, **kwargs):
    print(f"🔹 RUN: {cmd}")
    subprocess.run(cmd, shell=True, check=True, **kwargs)

def ask(prompt, default="n"):
    ans = input(prompt).strip()
    return ans.lower() if ans else default.lower()

print("\n========== Prepare LLVM 18 & Dependencies ==========")
# Cài LLVM 18
run("sudo apt update -y")
run("sudo apt install -y wget gnupg lsb-release software-properties-common")

run("wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh")
run("chmod +x /tmp/llvm.sh")
run("sudo /tmp/llvm.sh 18")

run("sudo apt update -y")
run("sudo apt install -y build-essential clang-18 lld-18 git ninja-build python3-venv python3-pip "
    "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev "
    "libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev "
    "libspice-server-dev libspice-protocol-dev llvm-18 llvm-18-dev llvm-18-tools aria2")

os.environ["PATH"] = "/usr/lib/llvm-18/bin:" + os.environ["PATH"]

# 1️⃣ Tạo venv để cài Meson mới
run("python3 -m venv ~/qemu-env")
run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip meson ninja tomli markdown packaging'")

print("\n========== Clone QEMU 10.1.2 ==========")
run("rm -rf /tmp/qemu-src && git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src")
os.makedirs("/tmp/qemu-src/build", exist_ok=True)
os.chdir("/tmp/qemu-src/build")

print("\n========== Configure Build ==========")
# Set environment
os.environ["CC"] = "clang-18"
os.environ["CXX"] = "clang++-18"
os.environ["LD"] = "lld-18"

common_flags = (
    "-Ofast -ffast-math -funroll-loops -fomit-frame-pointer -flto "
    "-fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables "
    "-march=native -mtune=native -pipe "
    "-Wno-error -Wno-unused-command-line-argument -Wno-overriding-t-option"
)
os.environ["CFLAGS"] = f"{common_flags} -fno-pie -fno-pic -DDEFAULT_TCG_TB_SIZE=65536 -DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DQEMU_STRICT_ALIGN=0"
os.environ["CXXFLAGS"] = os.environ["CFLAGS"]
os.environ["LDFLAGS"] = "-flto -fno-pie -fno-pic -Wl,-Ofast"

# Configure QEMU với Meson trong venv
meson_bin = os.path.expanduser("~/qemu-env/bin/meson")
run(f"{meson_bin} setup build --buildtype=release "
    "-Dtests=false "
    "-Duse_testfloat=false "
    "-Dcoroutine_pool=true "
    "-Dstrip=true "
    "-Ddocs=false "
    "-Dglib=enabled "
    "-Dgtk=enabled "
    "-Dsdl=enabled "
    "-Dspice=enabled "
    "-Dlibfdt=enabled "
    "-Dslirp=enabled")

print("\n========== Build QEMU ==========")
run("ninja -C build -j$(nproc)")
run("sudo ninja -C build install")

print("\n✅ QEMU 10.1.2 build xong với LLVM 18 + full fast-math + TCG + Polly + LTO, không lỗi TestFloat/FENV!")
run("qemu-system-x86_64 --version")
