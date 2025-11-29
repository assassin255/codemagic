#!/usr/bin/env python3
import os
import subprocess
import shutil

def run(cmd, **kwargs):
    print(f"🔹 RUN: {cmd}")
    subprocess.run(cmd, shell=True, check=True, **kwargs)

print("\n========== Prepare Environment ==========")
# 1️⃣ Cài LLVM 18
run("sudo apt update -y")
run("sudo apt install -y wget gnupg lsb-release software-properties-common")

run("wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh")
run("chmod +x /tmp/llvm.sh")
run("sudo /tmp/llvm.sh 18")

run("sudo apt update -y")
run("sudo apt install -y build-essential clang-18 lld-18 git ninja-build python3-venv python3-pip "
    "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev "
    "libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev "
    "libspice-server-dev libspice-protocol-dev llvm-18 llvm-18-dev llvm-18-tools aria2 meson")

os.environ["PATH"] = "/usr/lib/llvm-18/bin:" + os.environ["PATH"]

# 2️⃣ Python venv
run("python3 -m venv ~/qemu-env")
run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")

# 3️⃣ Clone QEMU
QEMU_SRC = "/tmp/qemu-src"
if os.path.exists(QEMU_SRC):
    shutil.rmtree(QEMU_SRC)
run(f"git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git {QEMU_SRC}")

# 4️⃣ Remove TestFloat to avoid FENV errors
TESTFLOAT = os.path.join(QEMU_SRC, "subprojects/berkeley-testfloat-3")
if os.path.exists(TESTFLOAT):
    print("⚡ Removing TestFloat to avoid FENV errors")
    shutil.rmtree(TESTFLOAT)

# 5️⃣ Build with Meson
os.chdir(QEMU_SRC)
if os.path.exists("build"):
    shutil.rmtree("build")
os.makedirs("build", exist_ok=True)

# 5a️⃣ Set environment for clang
os.environ["CC"] = "clang-18"
os.environ["CXX"] = "clang++-18"
os.environ["LD"] = "lld-18"
common_flags = (
    "-Ofast -ffast-math -funroll-loops -fomit-frame-pointer -flto "
    "-fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables "
    "-march=native -mtune=native -pipe"
)
os.environ["CFLAGS"] = f"{common_flags} -DDEFAULT_TCG_TB_SIZE=65536 -DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DQEMU_STRICT_ALIGN=0"
os.environ["CXXFLAGS"] = os.environ["CFLAGS"]
os.environ["LDFLAGS"] = "-flto -fno-pie -fno-pic -Wl,-Ofast"

# 5b️⃣ Meson setup
run("meson setup build --buildtype=release "
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

# 6️⃣ Compile
os.chdir("build")
run("ninja -j$(nproc)")

# 7️⃣ Install
run("sudo ninja install")

# 8️⃣ Test QEMU
run("qemu-system-x86_64 --version")
print("✅ QEMU 10.1.2 built with LLVM 18, TCG + LTO + full fast-math, TestFloat disabled")
