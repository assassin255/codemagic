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
# ASK BUILD QEMU
# ============================

print("\n=====================")
print("    BUILD QEMU ?")
print("=====================\n")

choice = ask("👉 Bạn có muốn build QEMU 10.1.2 từ source với tối ưu không? (y/n): ", "n")

if choice == "y":

    # QEMU đã có thì bỏ qua
    if subprocess.run("command -v qemu-system-x86_64", shell=True).returncode == 0:
        print("⚡ QEMU đã cài sẵn, bỏ qua build.\n")
    else:
        print("🚀 Build QEMU 10.1.2 + LLVM18 + Ofast + Polly + Vectorize + LTO\n")

        # 1. CÀI LLVM 18
        run("sudo apt update -y")
        run("sudo apt install -y wget gnupg lsb-release software-properties-common")

        run("wget https://apt.llvm.org/llvm.sh -O /tmp/llvm.sh")
        run("chmod +x /tmp/llvm.sh")
        run("sudo /tmp/llvm.sh 18")

        run("sudo apt update -y")
        run(
            "sudo apt install -y build-essential clang-18 lld-18 git ninja-build python3-venv python3-pip "
            "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev "
            "libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev "
            "libspice-server-dev libspice-protocol-dev llvm-18 llvm-18-dev llvm-18-tools aria2"
        )

        os.environ["PATH"] = "/usr/lib/llvm-18/bin:" + os.environ["PATH"]

        # 2. VENV
        run("python3 -m venv ~/qemu-env")
        run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")

        # 3. CLONE QEMU
        run("rm -rf /tmp/qemu-src")
        run("git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src")

        os.makedirs("/tmp/qemu-src/build", exist_ok=True)
        os.chdir("/tmp/qemu-src/build")

        # 4. ENV BUILD
        build_env = (
            "export CC=clang-18; "
            "export CXX=clang++-18; "
            "export LD=lld-18; "
            "export CFLAGS=\"-O3 -Ofast -fno-fast-math -frounding-math -ffp-contract=off "
            "-march=native -mtune=native -pipe -flto -fomit-frame-pointer -fno-semantic-interposition "
            "-mllvm -polly -mllvm -polly-vectorizer=stripmine\"; "
            "export CXXFLAGS=\"$CFLAGS\"; "
            "export LDFLAGS=\"-flto -Wl,-O3\"; "
        )

        # 5. CONFIGURE
        run(
            build_env +
            "../configure --target-list=x86_64-softmmu "
            "--enable-tcg --enable-slirp --enable-gtk --enable-sdl "
            "--enable-spice --enable-plugins --enable-lto "
            "--enable-coroutine-pool --disable-werror --disable-debug-info "
            "--disable-malloc-trim"
        )

        # 6. MAKE + INSTALL
        run("make -j$(nproc)")
        run("sudo make install")

        # 7. CLEAN
        run("rm -rf /tmp/qemu-src")
        run("deactivate || true")

        print("🔥 FUSION BUILD DONE: QEMU 10.1.2 + LLVM18 + Ofast + Polly + LTO")
        run("qemu-system-x86_64 --version")

else:
    print("⚡ Bỏ qua build QEMU.\n")


# ============================
# CHỌN WINDOWS
# ============================

print("\n=====================")
print("    CHỌN WINDOWS")
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
# DETECT CPU HOST
# ============================

cpu_host = subprocess.getoutput("grep -m1 'model name' /proc/cpuinfo | sed 's/^.*: //'").strip()
print(f"🧠 CPU host detected: {cpu_host}")

cpu_model = f'max,model-id="{cpu_host}"'

cpu_core = input("⚙ CPU core (default 2): ").strip() or "2"
ram_size = input("💾 RAM GB (default 4): ").strip() or "4"


# ============================
# START VM
# ============================

print("\n💻 Khởi động VM...")

start_cmd = f"""qemu-system-x86_64 \
-machine type=q35 \
-cpu {cpu_model} \
-smp {cpu_core} \
-m {ram_size}G \
-accel tcg,thread=multi,tb-size=8192,split-wx=off \
-object iothread,id=io1 \
-drive file=win.img,if=none,id=drive0,cache=unsafe,aio=threads,discard=on,format=raw \
-device virtio-blk-pci,drive=drive0 \
-vga virtio \
-device virtio-gpu-pci,id=video0 \
-device qemu-xhci,id=xhci \
-device usb-tablet,bus=xhci.0 \
-device usb-kbd,bus=xhci.0 \
-netdev user,id=n0,hostfwd=tcp::3389-:3389 \
-device virtio-net-pci,netdev=n0 \
-display vnc=:0 \
-boot order=c,menu=on \
-name "{WIN_NAME} VM" \
-daemonize \
> /dev/null 2>&1
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
    print("🚀 Chạy Tunnel TCP 3389")
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