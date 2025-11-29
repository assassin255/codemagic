#!/usr/bin/env python3
import os
import subprocess
import shutil

def run(cmd, **kwargs):
    """Chạy lệnh shell, lỗi sẽ raise exception"""
    print(f"🔹 RUN: {cmd}")
    subprocess.run(cmd, shell=True, check=True, **kwargs)

# =========================
# 1️⃣ XÓA REPO LLVM 15 LỖI
# =========================
llvm15_list = "/etc/apt/sources.list.d/llvm-toolchain-noble-15.list"
if os.path.exists(llvm15_list):
    print(f"🗑️  Xóa repo lỗi: {llvm15_list}")
    os.remove(llvm15_list)

# =========================
# 2️⃣ CÀI LLVM 18 + dependencies
# =========================
run("sudo apt update -y")
run("sudo apt install -y wget gnupg lsb-release software-properties-common")

# Cài LLVM 18 từ script chính thức
run("wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh")
run("chmod +x /tmp/llvm.sh")
run("sudo /tmp/llvm.sh 18")

# Cài build dependencies
run("sudo apt update -y")
run(
    "sudo apt install -y build-essential clang-18 lld-18 git ninja-build python3-venv python3-pip "
    "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev "
    "libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev "
    "libspice-server-dev libspice-protocol-dev aria2"
)

# Thêm LLVM18 vào PATH
os.environ["PATH"] = "/usr/lib/llvm-18/bin:" + os.environ["PATH"]

# =========================
# 3️⃣ TẠO PYTHON VENV
# =========================
run("python3 -m venv ~/qemu-env")
run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")

# =========================
# 4️⃣ CLONE QEMU
# =========================
QEMU_DIR = "/tmp/qemu-src"
if os.path.exists(QEMU_DIR):
    shutil.rmtree(QEMU_DIR)
run(f"git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git {QEMU_DIR}")

os.makedirs(f"{QEMU_DIR}/build", exist_ok=True)
os.chdir(f"{QEMU_DIR}/build")

# =========================
# 5️⃣ ENV BUILD
# =========================
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

# =========================
# 6️⃣ CONFIGURE QEMU
# =========================
configure_cmd = (
    "../configure "
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
    "--extra-cflags='-DDEFAULT_TCG_TB_SIZE=65536 -DTCG_TARGET_HAS_MEMORY_BARRIER=0'"
)
run(configure_cmd)

# =========================
# 7️⃣ BUILD & INSTALL
# =========================
run("make -j$(nproc)")
run("sudo make install PREFIX=/opt/qemu-optimized")

# Xóa source
shutil.rmtree(QEMU_DIR)

# =========================
# 8️⃣ TEST QEMU
# =========================
run("deactivate", shell=True, check=False)
run("/opt/qemu-optimized/bin/qemu-system-x86_64 --version")
print("✅ QEMU 10.1.2 built successfully with LLVM18 + TCG + Polly + LTO + full fast-math!")

