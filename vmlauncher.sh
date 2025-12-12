#!/usr/bin/env bash
#1

ask() {
    read -rp "$1" ans
    ans="${ans,,}"
    if [[ -z "$ans" ]]; then
        echo "$2"
    else
        echo "$ans"
    fi
}

choice=$(ask "👉 Bạn có muốn build QEMU 10.2.0-rc3 với LLVM21 tối ưu ULTRA không? (y/n): " "n")

if [[ "$choice" == "y" ]]; then
    if command -v qemu-system-x86_64 >/dev/null 2>&1; then
        echo "⚡ QEMU đã cài sẵn, bỏ qua build."
    else
        echo "🚀 Build QEMU 10.2.0-rc3 + LLVM21 ULTRA-Optimized"
        sudo apt update -y
        sudo apt install -y wget gnupg lsb-release software-properties-common build-essential ninja-build git python3 python3-venv python3-pip libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev libspice-server-dev libspice-protocol-dev pkg-config meson

        wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add -
        sudo add-apt-repository "deb http://apt.llvm.org/jammy/ llvm-toolchain-jammy-21 main"
        sudo apt update
        sudo apt install -y clang-21 lld-21 llvm-21 llvm-21-dev llvm-21-tools

        export PATH="/usr/lib/llvm-21/bin:$PATH"
        export CC=clang-21
        export CXX=clang++-21
        export LD=lld-21

        python3 -m venv ~/qemu-env
        source ~/qemu-env/bin/activate
        pip install --upgrade pip tomli markdown packaging

        rm -rf /tmp/qemu-src /tmp/qemu-build
        cd /tmp
        git clone --depth 1 --branch v10.2.0-rc3 https://gitlab.com/qemu-project/qemu.git qemu-src
        mkdir /tmp/qemu-build
        cd /tmp/qemu-build

        EXTRA_CFLAGS="-DDEFAULT_TCG_TB_SIZE=1048576 -DTCG_TARGET_HAS_MEMORY_BARRIER=0 -DTCG_ACCEL_FAST=1 -DTCG_OVERSIZED_OP=1 -DTCG_ENABLE_FAST_PREFETCH=1 -DQEMU_STRICT_ALIGN=0 -DTCG_TARGET_HAS_direct_jump=1 -DTCG_TARGET_HAS_JUMP_CACHE=1 -Ofast -ffast-math -march=native -mtune=native -pipe -flto=full -fuse-ld=lld -fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables -fno-unwind-tables -fno-stack-protector -fno-plt -fno-pic -fno-pie -fno-common -ffp-contract=fast -fno-trapping-math -fno-math-errno -fno-signed-zeros -fno-rounding-math -fno-signaling-nans -funroll-loops -finline-functions -finline-limit=1000000 -fmerge-all-constants -fvectorize -fprefetch-loop-arrays -fmodulo-sched -fmodulo-sched-allow-regmoves -faggressive-loop-coalescing -fipa-cp -fpredictive-commoning -falign-functions=32 -falign-loops=32 -falign-jumps=32"

        LDFLAGS="-flto=full -Wl,--lto-O3 -Wl,--icf=all -Wl,--lto-partitions=1 -Wl,--gc-sections"

        ../qemu-src/configure --prefix=/opt/qemu-optimized --target-list=x86_64-softmmu --enable-tcg --enable-slirp --enable-gtk --enable-sdl --enable-spice --enable-lto --enable-coroutine-pool --disable-debug-info --disable-malloc-trim --disable-plugins --disable-docs --disable-werror --disable-fdt CC="$CC" CXX="$CXX" LD="$LD" CFLAGS="$EXTRA_CFLAGS" CXXFLAGS="$EXTRA_CFLAGS" LDFLAGS="$LDFLAGS"

        ninja -j"$(nproc)"
        sudo ninja install

        if ! grep -q "/opt/qemu-optimized/bin" ~/.bashrc 2>/dev/null; then
            echo 'export PATH="/opt/qemu-optimized/bin:$PATH"' >> ~/.bashrc
        fi
        export PATH="/opt/qemu-optimized/bin:$PATH"
        if [ -f ~/.zshrc ]; then
            echo 'export PATH="/opt/qemu-optimized/bin:$PATH"' >> ~/.zshrc
        fi

        qemu-system-x86_64 --version
        echo "LLVM-21 + QEMU 10.2.0-rc3 TCG optimized build done"
    fi
else
    echo "⚡ Bỏ qua build QEMU."
fi

echo ""
echo "🪟 Chọn phiên bản Windows muốn tải:"
echo "1️⃣ Windows Server 2012 R2"
echo "2️⃣ Windows Server 2016"
echo "3️⃣ Windows Server 2022"
read -rp "👉 Nhập số [1-3]: " win_choice
case "$win_choice" in
    1) WIN_NAME="Windows2012"; WIN_URL="https://drive.muavps.net/file/Windows2012.img" ;;
    2) WIN_NAME="Windows2016"; WIN_URL="http://drive.muavps.net/file/Windows2016.img" ;;
    3) WIN_NAME="Windows2022"; WIN_URL="https://drive.muavps.net/file/Windows2022.img" ;;
    *) WIN_NAME="Windows2012"; WIN_URL="https://drive.muavps.net/file/Windows2012.img" ;;
esac
echo "💾 File VM: $WIN_NAME"

if [[ -f "win.img" ]]; then
    echo "✔ win.img đã tồn tại — skip tải."
else
    echo "⬇ Tải bằng aria2c..."
    aria2c -x16 -s16 --continue --file-allocation=none "$WIN_URL" -o win.img
fi

read -rp "📦 Mở rộng đĩa thêm bao nhiêu GB (default 20)? " extra_gb
extra_gb="${extra_gb:-20}"
qemu-img resize win.img "+${extra_gb}G"
echo "🔧 Đĩa đã mở rộng thêm $extra_gb GB."

cpu_host=$(grep -m1 "model name" /proc/cpuinfo | sed 's/^.*: //')
echo "🧠 CPU host detected: $cpu_host"
cpu_model="max,model-id=${cpu_host}"

read -rp "⚙ CPU core (default 2): " cpu_core
cpu_core="${cpu_core:-2}"
read -rp "💾 RAM GB (default 4): " ram_size
ram_size="${ram_size:-4}"

echo "💻 Khởi động VM..."

run_vm() {
    qemu-system-x86_64 \
    -machine type=q35 \
    -cpu "$cpu_model" \
    -smp "$cpu_core" \
    -m "${ram_size}G" \
    -accel tcg,thread=multi,tb-size=1048576,split-wx=off \
    -object iothread,id=io1 \
    -drive file=win.img,if=none,id=drive0,cache=unsafe,aio=threads,discard=on,format=raw \
    -device ide-hd,drive=drive0,bus=ide.0 \
    -vga virtio \
    -device qemu-xhci,id=xhci \
    -device usb-tablet,bus=xhci.0 \
    -device usb-kbd,bus=xhci.0 \
    -netdev user,id=n0,hostfwd=tcp::3389-:3389 \
    -device virtio-net-pci,netdev=n0 \
    -display vnc=:0 \
    -boot order=c,menu=on \
    -name "${WIN_NAME} VM" \
    -daemonize \
    > /dev/null 2>&1
}

run_vm
sleep 3

use_rdp=$(ask "🛰️ Có muốn dùng RDP để kết nối đến VM không? (y/n): " "n")
if [[ "$use_rdp" == "y" ]]; then
    wget -q https://github.com/kami2k1/tunnel/releases/latest/download/kami-tunnel-linux-amd64.tar.gz
    tar -xzf kami-tunnel-linux-amd64.tar.gz
    chmod +x kami-tunnel
    sudo apt install -y tmux
    echo "🚀 Chạy Tunnel TCP 3389"
    tmux kill-session -t kami 2>/dev/null || true
    tmux new-session -d -s kami "./kami-tunnel 3389"
    sleep 2
    PUBLIC=$(tmux capture-pane -pt kami | grep "Public:" | head -n 1 | awk '{print $2}')
    echo ""
    echo "📡 Public IP: $PUBLIC"
    echo "💻 Username: administrator"
    echo "🔑 Password: Datnguyentv.com"
    echo "⏳ Đợi 3-5 phút để login"
else
    echo "❌ Bỏ qua tunnel RDP."
fi

echo "🎉 VM sẵn sàng!"
