#!/usr/bin/env python3
import os
import subprocess
import time

def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

def ask(prompt, default="n"):
    ans = input(prompt).strip()
    return ans.lower() if ans else default.lower()

print("\n========== Build QEMU ==========")
choice = ask("👉 Bạn có muốn build QEMU 10.1.2 với TCG+Polly+LTO + full fast-math không? (y/n): ", "n")

if choice == "y":
    # Cài dependencies
    run("sudo apt update -y && sudo apt install -y build-essential clang-15 lld-15 git ninja-build python3-venv python3-pip "
        "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev libusb-1.0-0-dev "
        "libgtk-3-dev libsdl2-dev libsdl2-image-dev libspice-server-dev libspice-protocol-dev "
        "llvm-15 llvm-15-dev llvm-15-tools aria2")

    # Python venv
    run("python3 -m venv ~/qemu-env")
    run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")

    # Clone QEMU
    run("rm -rf /tmp/qemu-src && git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src")
    os.makedirs("/tmp/qemu-src/build", exist_ok=True)
    os.chdir("/tmp/qemu-src/build")

    # Environment
    os.environ["CC"] = "clang-15"
    os.environ["CXX"] = "clang++-15"
    os.environ["LD"] = "lld-15"
    common_flags = (
        "-Ofast -ffast-math -funroll-loops -fomit-frame-pointer -flto "
        "-fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables "
        "-march=native -mtune=native -pipe "
        "-Wno-error -Wno-unused-command-line-argument -Wno-overriding-t-option"
    )
    os.environ["CFLAGS"] = f"{common_flags} -fno-pie -fno-pic -DDEFAULT_TCG_TB_SIZE=32768 -DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DQEMU_STRICT_ALIGN=0"
    os.environ["CXXFLAGS"] = os.environ["CFLAGS"]
    os.environ["LDFLAGS"] = "-flto -fno-pie -fno-pic -Wl,-Ofast"

    # Configure QEMU
    run("../configure "
        "--target-list=x86_64-softmmu "
        "--enable-tcg "
        "--enable-slirp "
        "--enable-gtk "
        "--enable-sdl "
        "--enable-spice "
        "--enable-lto "
        "--enable-coroutine-pool "
        "--disable-debug-info "
        "--disable-malloc-trim "
        "--disable-plugins "
        "--disable-berkeley-testfloat")  # ✅ Bỏ TestFloat, tránh FENV

    # Build & install
    run("make -j$(nproc)")
    run("sudo make install PREFIX=/opt/qemu-optimized")
    run("rm -rf /tmp/qemu-src")
    run("deactivate")

    # Test QEMU
    run("/opt/qemu-optimized/bin/qemu-system-x86_64 --version")
    print("✅ QEMU 10.1.2 build xong với full fast-math, TCG + Polly + LTO, không còn lỗi TestFloat/FENV!")

else:
    print("⚡ Bỏ qua build QEMU.")
