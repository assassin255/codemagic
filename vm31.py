#!/usr/bin/env python3
import os
import subprocess
import time

def run(cmd):
    subprocess.run(cmd, shell=True, check=False)

def ask(prompt, default="n"):
    ans = input(prompt).strip()
    return ans.lower() if ans else default.lower()

print("BUILD QEMU 10.1.2 + LLVM15 + PGO + BOLT + LTO")

choice = ask("Build QEMU optimized? (y/n): ", "n")

if choice == "y":
    run("sudo apt update -y")
    run("sudo apt install -y build-essential clang-15 lld-15 git ninja-build python3-venv python3-pip libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev libspice-server-dev libspice-protocol-dev llvm-15 llvm-15-dev llvm-15-tools aria2")
    os.environ["PATH"] = "/usr/lib/llvm-15/bin:" + os.environ["PATH"]

    run("rm -rf ~/qemu-llvm15-build")
    run("mkdir -p ~/qemu-llvm15-build")
    PREFIX = os.path.expanduser("~/qemu-llvm15-build")

    run("python3 -m venv ~/qemu-env")
    run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")

    run("rm -rf /tmp/qemu-src")
    run("git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src")

    os.makedirs("/tmp/qemu-src/build", exist_ok=True)
    os.chdir("/tmp/qemu-src/build")

    base = "export CC=clang-15; export CXX=clang++-15; export LD=lld-15; export COMMON='-O3 -march=native -mtune=native -pipe -flto -funroll-loops -fomit-frame-pointer -fno-semantic-interposition -mllvm -polly -mllvm -polly-vectorizer=stripmine'; "

    run(base + "export CFLAGS=\"$COMMON -fprofile-generate=/tmp/qemu-prof\"; export CXXFLAGS=\"$CFLAGS\"; export LDFLAGS='-flto -Wl,-O3'; ../configure --prefix=" + PREFIX + " --target-list=x86_64-softmmu --enable-tcg --enable-slirp --enable-gtk --enable-sdl --enable-spice --enable-plugins --enable-lto --enable-coroutine-pool --disable-werror --disable-debug-info --disable-malloc-trim")
    run("make -j$(nproc)")
    run("make install")

    os.environ["PATH"] = PREFIX + "/bin:" + os.environ["PATH"]
    run("qemu-system-x86_64 --version")
    run("qemu-img --version")

    if os.path.isdir("/tmp/qemu-prof"):
        raws = " ".join("/tmp/qemu-prof/" + f for f in os.listdir("/tmp/qemu-prof") if f.endswith(".profraw"))
        if raws:
            run("llvm-profdata merge -output=/tmp/qemu.profdata " + raws)

    os.chdir("/tmp/qemu-src/build")
    run("make clean")
    run(base + "export CFLAGS=\"$COMMON -fprofile-use=/tmp/qemu.profdata -fprofile-correction\"; export CXXFLAGS=\"$CFLAGS\"; export LDFLAGS='-flto -Wl,-O3'; ../configure --prefix=" + PREFIX + " --target-list=x86_64-softmmu --enable-tcg --enable-slirp --enable-gtk --enable-sdl --enable-spice --enable-plugins --enable-lto --enable-coroutine-pool --disable-werror --disable-debug-info --disable-malloc-trim")
    run("make -j$(nproc)")
    run("make install")

    run("rm -rf /tmp/qemu-prof /tmp/qemu.profdata")

    qemu_bin = PREFIX + "/bin/qemu-system-x86_64"
    bolt = subprocess.run("command -v llvm-bolt", shell=True).returncode == 0

    if bolt:
        run("cp " + qemu_bin + " " + qemu_bin + ".orig")
        run("llvm-bolt " + qemu_bin + ".orig -o " + qemu_bin + ".bolt --reorder-blocks=cache+ --reorder-functions=hot --split-functions --data-refs --dedup-strings --symbolic")
        run("mv -f " + qemu_bin + ".bolt " + qemu_bin)

    run("rm -rf /tmp/qemu-src")
    run("deactivate || true")

    os.chdir(os.path.expanduser("~"))
    run("tar -czf qemu_llvm15_build.tar.gz qemu-llvm15-build")

    print("DONE: qemu_llvm15_build.tar.gz READY")

print("Build complete.")
