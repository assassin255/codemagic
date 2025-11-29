#!/usr/bin/env python3
import os
import subprocess
import time

def run(cmd):
    subprocess.run(cmd, shell=True, check=False)

def ask(prompt, default="n"):
    ans = input(prompt).strip()
    return ans.lower() if ans else default.lower()

print("\n========== Build QEMU ==========")
choice = ask("👉 Bạn có muốn build QEMU 10.1.2 với TCG+Polly+LTO + fast-math không FENV? (y/n): ", "n")

if choice == "y":
    run("sudo apt update -y && sudo apt install -y build-essential clang-15 lld-15 git ninja-build python3-venv python3-pip "
        "libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev libusb-1.0-0-dev "
        "libgtk-3-dev libsdl2-dev libsdl2-image-dev libspice-server-dev libspice-protocol-dev "
        "llvm-15 llvm-15-dev llvm-15-tools aria2")
    os.environ["PATH"] = "/usr/lib/llvm-15/bin:" + os.environ["PATH"]
    run("python3 -m venv ~/qemu-env")
    run("bash -c 'source ~/qemu-env/bin/activate && pip install --upgrade pip tomli markdown packaging'")
    run("rm -rf /tmp/qemu-src")
    run("git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src")
    os.makedirs("/tmp/qemu-src/build", exist_ok=True)
    os.chdir("/tmp/qemu-src/build")

    env_base = (
        "export CC=clang-15; "
        "export CXX=clang++-15; "
        "export LD=lld-15; "
        "export COMMON='-Ofast -ffast-math -funroll-loops -fomit-frame-pointer -flto "
        "-fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables "
        "-march=native -mtune=native -pipe -Wno-error -Wno-unused-command-line-argument -Wno-overriding-t-option'"
    )

    run(
        env_base +
        " && export CFLAGS=\"$COMMON -fno-pie -fno-pic -DDEFAULT_TCG_TB_SIZE=32768 "
        "-DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DQEMU_STRICT_ALIGN=0\""
        " && export CXXFLAGS=\"$CFLAGS\""
        " && export LDFLAGS='-flto -fno-pie -fno-pic -Wl,-Ofast'"
        " && ../configure "
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
        "--disable-plugins"
    )

    run("make -j$(nproc)")
    run("sudo make install PREFIX=/opt/qemu-optimized")
    run("rm -rf /tmp/qemu-src")
    run("deactivate")
    run("/opt/qemu-optimized/bin/qemu-system-x86_64 --version")
    print("✅ QEMU 10.1.2 built với TCG+Polly+LTO + fast-math, bỏ FENV hoàn toàn!")

else:
    print("⚡ Bỏ qua build QEMU.")

print("\n========== Download & Run VM ==========")
print("\n=====================")
print("    CHỌN WINDOWS MUỐN TẢI")
print("=====================\n")

print("1️⃣ Windows Server 2012 R2")
print("2️⃣ Windows Server 2016")
print("3️⃣ Windows Server 2022")

win_choice = input("👉 Nhập số [1-3]: ").strip()
urls = {
    "1": ("Windows2012", "https://drive.muavps.net/file/Windows2012.img"),
    "2": ("Windows2016", "http://drive.muavps.net/file/Windows2016.img"),
    "3": ("Windows2022", "https://drive.muavps.net/file/Windows2022.img")
}
WIN_NAME, WIN_URL = urls.get(win_choice, urls["1"])
print(f"💾 File VM: {WIN_NAME}")

if os.path.exists("win.img"):
    print("✔ win.img đã tồn tại — skip tải.")
else:
    print("⬇ Tải bằng aria2c...")
    run(f'aria2c -x16 -s16 --continue --file-allocation=none "{WIN_URL}" -o win.img')

extra_gb = input("📦 Mở rộng đĩa thêm bao nhiêu GB (default 20)? ").strip() or "20"
run(f"/opt/qemu-optimized/bin/qemu-img resize win.img +{extra_gb}G")
print(f"🔧 Đĩa đã mở rộng {extra_gb} GB.")

cpu_host = subprocess.getoutput("grep -m1 'model name' /proc/cpuinfo | sed 's/^.*: //'").strip()
print(f"🧠 CPU host detected: {cpu_host}")

cpu_core = input("⚙ CPU core (default 2): ").strip() or "2"
ram_size = input("💾 RAM GB (default 4): ").strip() or "4"

start_cmd = f"""/opt/qemu-optimized/bin/qemu-system-x86_64 \
-machine type=q35 \
-cpu max,model-id='{cpu_host}' \
-smp {cpu_core} \
-m {ram_size}G \
-accel tcg,thread=multi,tb-size=32768,split-wx=off \
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
-name '{WIN_NAME} VM' \
-daemonize
"""

print("💻 Khởi động VM...")
run(start_cmd)
time.sleep(3)

use_rdp = ask("🛰️ Dùng RDP tunnel? (y/n): ", "n")
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
    print("⏳ Vui lòng đợi 3-5 phút rồi đăng nhập vào VM")
else:
    print("❌ Bỏ qua tunnel RDP.")
