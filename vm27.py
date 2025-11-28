#!/usr/bin/env python3
import os
import subprocess
import time

# ============================
# Helper functions
# ============================
def run(cmd):
    subprocess.run(cmd, shell=True, check=False)

def ask(prompt, default="n"):
    ans = input(prompt).strip()
    return ans.lower() if ans else default.lower()

# ============================
# INSTALL LLVM 15
# ============================
choice = ask("👉 Cài LLVM 15 và clang-15 chưa? (y/n): ", "y")
if choice == "y":
    run("sudo apt update -y && sudo apt install -y wget gnupg lsb-release software-properties-common")
    run("wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh")
    run("chmod +x /tmp/llvm.sh")
    run("sudo /tmp/llvm.sh 15")
    os.environ["PATH"] = "/usr/lib/llvm-15/bin:" + os.environ["PATH"]
    print("✅ LLVM 15 và clang-15 đã cài xong")

# ============================
# BUILD QEMU 10.1.2 WITH PGO + ADVANCED BOLT
# ============================
choice = ask("👉 Bạn có muốn build QEMU 10.1.2 từ source với PGO + BOLT nâng cao không? (y/n): ", "n")
if choice == "y":
    if subprocess.run("command -v qemu-system-x86_64", shell=True).returncode == 0:
        print("⚡ QEMU đã cài sẵn, bỏ qua build.\n")
    else:
        # install dependencies
        run("sudo apt update -y")
        run("sudo apt install -y build-essential git ninja-build python3-venv aria2 perf "
            "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev "
            "libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev "
            "libspice-server-dev libspice-protocol-dev")

        # python venv
        run("python3 -m venv ~/qemu-env")
        run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")

        # clone qemu
        run("rm -rf /tmp/qemu-src")
        run("git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src")
        os.makedirs("/tmp/qemu-src/build", exist_ok=True)
        os.chdir("/tmp/qemu-src/build")

        env_base = (
            "export PATH=/usr/lib/llvm-15/bin:$PATH; "
            "export CC=clang-15; "
            "export CXX=clang++-15; "
            "export LD=lld-15; "
            "export COMMON='-O3 -march=native -mtune=native -pipe -flto -fomit-frame-pointer -fno-semantic-interposition'; "
        )

        # STAGE A: generate PGO profile
        run(env_base + "export CFLAGS=\"$COMMON -fprofile-generate=/tmp/qemu-pgo-data\"; "
                        "export CXXFLAGS=\"$CFLAGS\"; "
                        "export LDFLAGS='-flto -Wl,-O3'; "
                        "../configure --target-list=x86_64-softmmu --enable-tcg --enable-slirp "
                        "--enable-gtk --enable-sdl --enable-spice --enable-plugins --enable-lto "
                        "--enable-coroutine-pool --disable-werror --disable-debug-info --disable-malloc-trim")
        run("make -j$(nproc)")
        run("sudo make install DESTDIR=/tmp/qemu-pgo-install || sudo make install")

        # STAGE B: run workload
        os.environ["PATH"] = "/tmp/qemu-pgo-install/usr/local/bin:" + os.environ["PATH"]
        workload_cmds = [
            "qemu-system-x86_64 --version",
            "qemu-img --version",
            "qemu-system-x86_64 -h | head -n 5"
        ]
        for cmd in workload_cmds:
            run(cmd)

        profdir = "/tmp/qemu-pgo-data"
        if os.path.isdir(profdir):
            profraws = " ".join([os.path.join(profdir, f) for f in os.listdir(profdir) if f.endswith(".profraw")])
            if profraws:
                run(f"llvm-profdata merge -output=/tmp/qemu_pgo.profdata {profraws}")

        # STAGE C: rebuild with PGO profile
        os.chdir("/tmp/qemu-src/build")
        run(env_base + "export CFLAGS=\"$COMMON -fprofile-use=/tmp/qemu_pgo.profdata -fprofile-correction\"; "
                        "export CXXFLAGS=\"$CFLAGS\"; "
                        "export LDFLAGS='-flto -Wl,-O3'; "
                        "make -j$(nproc) clean; "
                        "../configure --target-list=x86_64-softmmu --enable-tcg --enable-slirp "
                        "--enable-gtk --enable-sdl --enable-spice --enable-plugins --enable-lto "
                        "--enable-coroutine-pool --disable-werror --disable-debug-info --disable-malloc-trim; "
                        "make -j$(nproc)")
        run("sudo make install")

        # STAGE D: BOLT post-link nâng cao với perf và flags mở rộng
        qemu_bin = subprocess.getoutput("command -v qemu-system-x86_64").strip()
        if qemu_bin and subprocess.run("command -v llvm-bolt", shell=True).returncode == 0:
            run(f"sudo cp {qemu_bin} {qemu_bin}.orig")
            run(f"sudo perf record -e cycles:u -a -- {qemu_bin} --version")
            run(f"sudo llvm-bolt {qemu_bin}.orig -o {qemu_bin}.bolt "
                "--reorder-blocks=cache+ "
                "--reorder-blocks=ext-tsp "
                "--reorder-functions=hot "
                "--split-functions "
                "--split-eh "
                "--data-refs "
                "--dedup-strings "
                "--symbolic "
                "-prof=perf.data")
            run(f"sudo mv -f {qemu_bin}.bolt {qemu_bin}")

        # cleanup
        run("rm -rf /tmp/qemu-pgo-data /tmp/qemu_pgo.profdata /tmp/qemu-pgo-install /tmp/qemu-src")
        run("deactivate || true")
