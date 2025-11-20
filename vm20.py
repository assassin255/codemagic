#!/usr/bin/env python3
import os
import subprocess
import time

def run(cmd):
    subprocess.run(cmd, shell=True, check=False)

def ask(prompt, default="n"):
    ans = input(prompt).strip()
    return ans.lower() if ans else default.lower()

def check_qemu():
    return subprocess.run("command -v qemu-system-x86_64", shell=True).returncode == 0

# =====================
# BUILD QEMU
# =====================
choice = ask("👉 Bạn có muốn build QEMU 10.1.2 từ source không? (y/n): ", "n")
if choice == "y":
    if check_qemu():
        print("⚡ QEMU đã cài sẵn, bỏ qua build.")
    else:
        print("🚀 Build QEMU 10.1.2 + VM Optimized")
        build_cmds = [
            "sudo apt update -y",
            "sudo apt install -y build-essential clang-15 lld-15 git ninja-build python3-venv "
            "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev "
            "libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev "
            "libspice-server-dev libspice-protocol-dev llvm-15 llvm-15-dev llvm-15-tools aria2",
            "python3 -m venv ~/qemu-env",
            ". ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging",
            "rm -rf /tmp/qemu-src",
            "git clone https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src",
            "cd /tmp/qemu-src && git checkout v10.1.2 && mkdir -p build && cd build",
            "export CC=clang-15 CXX=clang++-15 LD=lld-15",
            ("export CFLAGS='-O3 -march=native -mtune=native -pipe -flto -fomit-frame-pointer "
             "-fno-exceptions -fno-rtti -fvisibility=hidden -fno-stack-protector -mllvm -polly'"),
            "export CXXFLAGS=\"$CFLAGS\"",
            "export LDFLAGS='-flto -fuse-ld=lld'",
            ("../configure --target-list=x86_64-softmmu --enable-tcg --enable-slirp --enable-gtk "
             "--enable-sdl --enable-spice --enable-plugins --enable-lto --enable-coroutine-pool "
             "--disable-werror --disable-debug-info --disable-malloc-trim"),
            "make -j$(nproc)",
            "sudo make install",
            "cd ~",
            "rm -rf /tmp/qemu-src",
            "deactivate",
            "qemu-system-x86_64 --version"
        ]
        # Chạy từng lệnh qua bash
        for cmd in build_cmds:
            run(f"bash -c '{cmd}'")
else:
    print("⚡ Bỏ qua build QEMU.")

# =====================
# CHỌN WINDOWS
# =====================
print("\n🪟 Chọn phiên bản Windows Server muốn tải:")
print("1️⃣ Windows 10 Pro LTSB 2016")
print("2️⃣ Windows 11 Pro")
print("3️⃣ Windows 10 Lite OS")

win_choice = input("👉 Nhập số [1-3]: ").strip()
urls = {
    "1": ("Windows2016", "https://archive.org/download/tamdz-w-10-2016/TamdzW10-2016.img"),
    "2": ("Windows11", "https://archive.org/download/tamdz-w-11/TamdzW11.img"),
    "3": ("Windows10lite", "https://archive.org/download/tamdz-w-10/TamdzW10.img")
}
WIN_NAME, WIN_URL = urls.get(win_choice, urls["1"])
print(f"💾 File VM: {WIN_NAME}")

# =====================
# DOWNLOAD
# =====================
if os.path.exists("win.img"):
    print("✔ win.img đã tồn tại — skip tải.")
else:
    print("⬇ Tải bằng aria2c (12 luồng, safe)...")
    run(f'aria2c -x12 -s12 --continue --file-allocation=none "{WIN_URL}" -o win.img')

# =====================
# RESIZE
# =====================
extra_gb = input("📦 Mở rộng đĩa thêm bao nhiêu GB (default 20)? ").strip() or "20"
run(f"qemu-img resize win.img +{extra_gb}G")
print(f"🔧 Đĩa đã mở rộng {extra_gb} GB.")

# =====================
# CPU DETECT
# =====================
cpu_output = subprocess.getoutput("lscpu | grep 'Model name'").lower()
if "xeon" in cpu_output:
    CPU_MODEL = "Cascadelake-Server-v5"
elif "epyc" in cpu_output:
    CPU_MODEL = "EPYC"
else:
    CPU_MODEL = "Westmere"

print("🧠 CPU host:", cpu_output)
cpu_core = input("⚙ CPU core (default 2): ").strip() or "2"
ram_size = input("💾 RAM GB (default 4): ").strip() or "4"

# =====================
# START VM (VirtIO Disk)
# =====================
print("💻 Khởi động VM với VirtIO disk...")
start_cmd = f"""qemu-system-x86_64 \
  -machine type=q35 \
  -cpu {CPU_MODEL} \
  -smp {cpu_core} \
  -m {ram_size}G \
  -accel tcg,thread=multi,tb-size=8192,split-wx=off \
  -object iothread,id=io1 \
  -drive file=win.img,if=none,id=drive0,format=raw,cache=unsafe,aio=threads,discard=on \
  -device ide-hd,drive=drive0,bus=ide.0 \
  -vga virtio \
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

# =====================
# RDP TUNNEL
# =====================
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

    USERNAME = "Administrator" if WIN_NAME == "Windows2016" else "Admin"

    print("\n📡 Public IP:", PUBLIC)
    print(f"💻 Username: {USERNAME}")
    print("🔑 Password: Nguyentam@123")
    print("⏳ Vui lòng đợi 3-5 phút rồi hãy đăng nhập vào VM")
else:
    print("❌ Bỏ qua tunnel RDP.")
