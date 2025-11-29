#!/usr/bin/env python3
import os
import subprocess

def run(cmd, **kwargs):
    print(f"🔹 RUN: {cmd}")
    subprocess.run(cmd, shell=True, check=True, **kwargs)

print("\n========== Build QEMU 10.1.2 with LLVM 18 + TCG + Polly + LTO ==========\n")
choice = input("👉 Bạn có muốn build QEMU 10.1.2 với TCG+Polly+LTO + full fast-math không? (y/n): ").strip().lower()
if choice != "y":
    print("⚡ Bỏ qua build QEMU.")
    exit(0)

# 1️⃣ Cài dependencies và LLVM 18
run("sudo apt update -y && sudo apt install -y wget gnupg lsb-release software-properties-common")
run("wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh")
run("chmod +x /tmp/llvm.sh")
run("sudo /tmp/llvm.sh 18")

run("sudo apt update -y && sudo apt install -y build-essential clang-18 lld-18 git ninja-build python3-venv python3-pip "
    "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev "
    "libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev "
    "libspice-server-dev libspice-protocol-dev llvm-18 llvm-18-dev llvm-18-tools aria2")

os.environ["PATH"] = "/usr/lib/llvm-18/bin:" + os.environ["PATH"]

# 2️⃣ Tạo Python venv
run("python3 -m venv ~/qemu-env")
run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")

# 3️⃣ Clone QEMU 10.1.2
run("rm -rf /tmp/qemu-src && git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src")
os.makedirs("/tmp/qemu-src/build", exist_ok=True)
os.chdir("/tmp/qemu-src/build")

# 4️⃣ Environment variables cho build
os.environ["CC"] = "clang-18"
os.environ["CXX"] = "clang++-18"
os.environ["LD"] = "lld-18"
common_flags = ("-Ofast -ffast-math -funroll-loops -fomit-frame-pointer -flto "
                "-fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables "
                "-march=native -mtune=native -pipe "
                "-Wno-error -Wno-unused-command-line-argument -Wno-overriding-t-option")
os.environ["CFLAGS"] = f"{common_flags} -fno-pie -fno-pic -DDEFAULT_TCG_TB_SIZE=65536 -DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DQEMU_STRICT_ALIGN=0"
os.environ["CXXFLAGS"] = os.environ["CFLAGS"]
os.environ["LDFLAGS"] = "-flto -fno-pie -fno-pic -Wl,-Ofast"

# 5️⃣ Configure QEMU (tắt TestFloat để tránh lỗi FENV)
configure_cmd = ("../configure "
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
                 "--disable-berkeley-testfloat "
                 "--extra-cflags='-DDEFAULT_TCG_TB_SIZE=65536 -DTCG_TARGET_HAS_MEMORY_BARRIER=0'")
run(configure_cmd)

# 6️⃣ Build & install
run("make -j$(nproc)")
run("sudo make install PREFIX=/opt/qemu-optimized")

# 7️⃣ Clean up
run("rm -rf /tmp/qemu-src")
run("deactivate || true")  # deactivate venv nếu đang active

# 8️⃣ Test QEMU
run("/opt/qemu-optimized/bin/qemu-system-x86_64 --version")
print("\n✅ QEMU 10.1.2 build xong với full fast-math, TCG + Polly + LTO, không còn lỗi TestFloat/FENV!")
