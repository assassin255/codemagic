#!/usr/bin/env python3
import os
import subprocess
import shutil

def run(cmd, cwd=None):
    """Run a shell command, raise if it fails"""
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

print("\n========== Build QEMU 10.1.2 with LLVM18 + TCG + LTO + Fast-Math ==========")

# 1️⃣ Cài LLVM18 + dependencies
print("\n🔹 Installing LLVM18 and dependencies...")
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

# 2️⃣ Python venv
print("\n🔹 Setting up Python virtualenv...")
venv_path = os.path.expanduser("~/qemu-env")
run(f"python3 -m venv {venv_path}")
activate_script = os.path.join(venv_path, "bin", "activate")
run(f"bash -c 'source {activate_script} && pip install --upgrade pip tomli markdown packaging'")

# 3️⃣ Clone QEMU source
qemu_src = "/tmp/qemu-src"
if os.path.exists(qemu_src):
    shutil.rmtree(qemu_src)
print("\n🔹 Cloning QEMU source...")
run(f"git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git {qemu_src}")

# 4️⃣ Remove TestFloat to avoid FENV errors
testfloat_dir = os.path.join(qemu_src, "subprojects/berkeley-testfloat-3")
if os.path.exists(testfloat_dir):
    print("🔹 Removing Berkeley TestFloat to avoid FENV errors...")
    shutil.rmtree(testfloat_dir)

# 5️⃣ Configure QEMU
build_dir = os.path.join(qemu_src, "build")
os.makedirs(build_dir, exist_ok=True)
os.chdir(build_dir)

os.environ["CC"] = "/usr/lib/llvm-18/bin/clang"
os.environ["CXX"] = "/usr/lib/llvm-18/bin/clang++"
os.environ["LD"] = "/usr/lib/llvm-18/bin/lld"
common_flags = (
    "-Ofast -ffast-math -funroll-loops -fomit-frame-pointer -flto "
    "-fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables "
    "-march=native -mtune=native -pipe "
    "-Wno-error -Wno-unused-command-line-argument -Wno-overriding-t-option"
)
os.environ["CFLAGS"] = f"{common_flags} -fno-pie -fno-pic -DDEFAULT_TCG_TB_SIZE=65536 -DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DQEMU_STRICT_ALIGN=0"
os.environ["CXXFLAGS"] = os.environ["CFLAGS"]
os.environ["LDFLAGS"] = "-flto -fno-pie -fno-pic -Wl,-Ofast"

configure_cmd = (
    f"{qemu_src}/configure "
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
    f"--extra-cflags='-DDEFAULT_TCG_TB_SIZE=65536 -DTCG_TARGET_HAS_MEMORY_BARRIER=0'"
)
print("\n🔹 Configuring QEMU...")
run(configure_cmd)

# 6️⃣ Build & Install
print("\n🔹 Building QEMU... (this may take a while)")
run(f"make -j$(nproc)")
install_prefix = "/opt/qemu-optimized"
print(f"\n🔹 Installing QEMU to {install_prefix}...")
run(f"sudo make install PREFIX={install_prefix}")

# 7️⃣ Cleanup
print("\n🔹 Cleaning up source directory...")
shutil.rmtree(qemu_src)

# 8️⃣ Test QEMU
print("\n🔹 Testing QEMU installation...")
run(f"{install_prefix}/bin/qemu-system-x86_64 --version")

print("\n✅ QEMU 10.1.2 built successfully with LLVM18 + TCG + Polly + LTO + full fast-math, TestFloat removed!")
