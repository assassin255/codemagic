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
# BUILD QEMU 10.1.2 WITH PGO + BOLT + POLLY + FULL LTO + MAX TCG
# ============================
choice = ask("👉 Bạn có muốn build QEMU 10.1.2 từ source với PGO + BOLT + Polly không? (y/n): ", "n")

if choice == "y":
    if subprocess.run("command -v qemu-system-x86_64", shell=True).returncode == 0:
        print("⚡ QEMU đã cài sẵn, bỏ qua build.\n")
    else:
        # Install LLVM15 + tools
        run("sudo apt update -y")
        run("sudo apt install -y build-essential clang-15 lld-15 git ninja-build python3-venv python3-pip "
            "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev "
            "libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev "
            "libspice-server-dev libspice-protocol-dev llvm-15 llvm-15-dev llvm-15-tools aria2")
        os.environ["PATH"] = "/usr/lib/llvm-15/bin:" + os.environ["PATH"]

        # Python venv
        run("python3 -m venv ~/qemu-env")
        run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")

        # Clone QEMU
        run("rm -rf /tmp/qemu-src")
        run("git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src")
        os.makedirs("/tmp/qemu-src/build", exist_ok=True)
        os.chdir("/tmp/qemu-src/build")

        # Env flags với Polly + vectorization + FULL LTO
        env_base = (
            "export CC=clang-15; "
            "export CXX=clang++-15; "
            "export LD=lld-15; "
            "export COMMON='-O3 -march=native -mtune=native -pipe -flto -funroll-loops -fomit-frame-pointer "
            "-fno-semantic-interposition -fstrict-aliasing -mllvm -polly "
            "-mllvm -polly-vectorizer=stripmine'; "
        )

        # STAGE A: generate profile
        run(env_base + "export CFLAGS=\"$COMMON -fprofile-generate=/tmp/qemu-pgo-data\"; "
                        "export CXXFLAGS=\"$CFLAGS\"; "
                        "export LDFLAGS='-flto -Wl,-O3'; "
                        "../configure --target-list=x86_64-softmmu --enable-tcg --enable-slirp --enable-gtk "
                        "--enable-sdl --enable-spice --enable-plugins --enable-lto --enable-coroutine-pool "
                        "--disable-werror --disable-debug-info --disable-malloc-trim")
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

        # STAGE C: rebuild với profile
        os.chdir("/tmp/qemu-src/build")
        run(env_base + "export CFLAGS=\"$COMMON -fprofile-use=/tmp/qemu_pgo.profdata -fprofile-correction\"; "
                        "export CXXFLAGS=\"$CFLAGS\"; "
                        "export LDFLAGS='-flto -Wl,-O3'; "
                        "make -j$(nproc) clean; "
                        "../configure --target-list=x86_64-softmmu --enable-tcg --enable-slirp --enable-gtk "
                        "--enable-sdl --enable-spice --enable-plugins --enable-lto --enable-coroutine-pool "
                        "--disable-werror --disable-debug-info --disable-malloc-trim; "
                        "make -j$(nproc)")
        run("sudo make install")

        # STAGE D: BOLT post-link
        qemu_bin = subprocess.getoutput("command -v qemu-system-x86_64").strip()
        if qemu_bin and subprocess.run("command -v llvm-bolt", shell=True).returncode == 0:
            run(f"sudo cp {qemu_bin} {qemu_bin}.orig")
            run(f"sudo llvm-bolt {qemu_bin}.orig -o {qemu_bin}.bolt --reorder-blocks=cache+ "
                "--reorder-functions=hotcold+ --split-functions --data-refs --dedup-strings --symbolic")
            run(f"sudo mv -f {qemu_bin}.bolt {qemu_bin}")

        # Cleanup
        run("rm -rf /tmp/qemu-pgo-data /tmp/qemu_pgo.profdata /tmp/qemu-pgo-install /tmp/qemu-src")
        run("deactivate || true")
        run("qemu-system-x86_64 --version")

# ============================
# CHỌN WINDOWS
# ============================
print("\n=====================")
print("    CHỌN WINDOWS MUỐN TẢI 💻")
print("=====================\n")
print("1️⃣ Windows Server 2012 R2")
print("2️⃣ Windows Server 2016")
print("3️⃣ Windows Server 2022")
win_choice = input("👉 Nhập số [1-3]: ").strip()
urls = {
    "1": ("Windows2012", "https://drive.muavps.net/file/Windows2012.img"),
    "2": ("Windows2016", "https://drive.muavps.net/file/Windows2016.img"),
    "3": ("Windows2022", "https://drive.muavps.net/file/Windows2022.img")
}
WIN_NAME, WIN_URL = urls.get(win_choice, urls["1"])
print(f"💾 File VM: {WIN_NAME}")

# ============================
# DOWNLOAD
# ============================
if os.path.exists("win.img"):
    print("✔ win.img đã tồn tại — skip tải.")
else:
    print("⬇ Tải bằng aria2c...")
    run(f'aria2c -x16 -s16 --continue --file-allocation=none "{WIN_URL}" -o win.img')

# ============================
# RESIZE
# ============================
extra_gb = input("📦 Mở rộng đĩa thêm bao nhiêu GB (default 20)? ").strip() or "20"
run(f"qemu-img resize win.img +{extra_gb}G")
print(f"🔧 Đĩa đã mở rộng {extra_gb} GB.")

# ============================
# NHẬP CPU & RAM (không auto detect)
# ============================
cpu_core = input("⚙ CPU core (default 2): ").strip() or "2"
ram_size = input("💾 RAM GB (default 4): ").strip() or "4"

# ============================
# START VM (MAX TCG OPTIMIZED)
# ============================
cpu_host = subprocess.getoutput("grep -m1 'model name' /proc/cpuinfo | sed 's/^.*: //'").strip()
print(f"🧠 CPU host detected: {cpu_host}")

print("\n💻 Khởi động VM...")
start_cmd = f"""qemu-system-x86_64 \
-machine type=q35 \
-cpu max,model-id="{cpu_host}" \
-smp {cpu_core} \
-m {ram_size}G \
-accel tcg,thread=multi,tb-size=16384,split-wx=off \
-object iothread,id=io1 \
-drive file=win.img,if=none,id=drive0,cache=writeback,aio=threads,discard=on,format=raw \
-device virtio-blk-pci,drive=drive0,iothread=io1 \
-vga virtio \
-device qemu-xhci,id=xhci \
-device usb-tablet,bus=xhci.0 \
-device usb-kbd,bus=xhci.0 \
-netdev user,id=n0,hostfwd=tcp::3389-:3389 \
-device virtio-net-pci,netdev=n0 \
-display vnc=:0 \
-boot order=c,menu=on \
-name "{WIN_NAME} VM" \
-daemonize
"""
run(start_cmd)
time.sleep(3)

# ============================
# RDP Tunnel
# ============================
use_rdp = ask("🛰️ Có muốn dùng RDP để kết nối đến VM không? (y/n): ", "n")
if use_rdp == "y":
    run("wget -q https://github.com/kami2k1/tunnel/releases/latest/download/kami-tunnel-linux-amd64.tar.gz")
    run("tar -xzf kami-tunnel-linux-amd64.tar.gz")
    run("chmod +x kami-tunnel")
    run("sudo apt install -y tmux")
    run("tmux kill-session -t kami 2>/dev/null || true")
    run("tmux new-session -d -s kami './kami-tunnel 3389'")
    time.sleep(2)
    PUBLIC = subprocess.getoutput("tmux capture-pane -pt kami | grep 'Public:' | head -n 1 | awk '{print $2}'")
    print("\n📡 Public IP:", PUBLIC)
    print("💻 Username: administrator")
    print("🔑 Password: Datnguyentv.com")
    print("⏳ Đợi 3–5 phút rồi đăng nhập VM")
else:
    print("❌ Bỏ qua tunnel RDP.")
