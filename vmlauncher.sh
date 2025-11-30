#!/usr/bin/env bash
set -e

ask() {
    read -rp "$1" ans
    ans="${ans,,}"
    if [[ -z "$ans" ]]; then
        echo "$2"
    else
        echo "$ans"
    fi
}

run() {
    bash -c "$1"
}

choice=$(ask "👉 Bạn có muốn build QEMU 10.1.2 từ source với tối ưu không? (y/n): " "n")

if [[ "$choice" == "y" ]]; then
    if command -v qemu-system-x86_64 >/dev/null 2>&1; then
        echo "⚡ QEMU đã cài sẵn, bỏ qua build."
    else
        echo "🚀 Build QEMU 10.1.2 + Optimized Flags"

        sudo apt update -y && sudo apt install -y wget gnupg lsb-release software-properties-common
        wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && sudo ./llvm.sh 18
        sudo apt update -y && sudo apt install -y clang-18 lld-18 llvm-18-dev llvm-18-tools build-essential git ninja-build python3-venv \
            libglib2.0-dev libpixman-1-dev zlib1g-dev libfdt-dev libslirp-dev libusb-1.0-0-dev libgtk-3-dev libsdl2-dev libsdl2-image-dev \
            libspice-server-dev libspice-protocol-dev python3-pip aria2

        export PATH="/usr/lib/llvm-18/bin:$PATH"
        python3 -m venv ~/qemu-env
        source ~/qemu-env/bin/activate
        pip install --upgrade pip tomli markdown packaging || true

        rm -rf /tmp/qemu-src
        git clone --depth 1 --branch v10.1.2 https://gitlab.com/qemu-project/qemu.git /tmp/qemu-src
        mkdir -p /tmp/qemu-src/build
        cd /tmp/qemu-src/build

        export CC=clang-18
        export CXX=clang++-18
        export LD=lld-18
        export EXTRA_CFLAGS="-Ofast -ffast-math -march=native -mtune=native -pipe -flto=full -fomit-frame-pointer \
-fno-semantic-interposition -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables -fno-unwind-tables -fno-stack-protector \
-ffp-contract=fast -fno-trapping-math -fno-math-errno -funroll-loops -finline-functions -fvectorize -fprefetch-loop-arrays \
-mllvm -polly -mllvm -polly-vectorizer=superword"
        export CFLAGS="$EXTRA_CFLAGS"
        export CXXFLAGS="$EXTRA_CFLAGS"
        export LDFLAGS="-flto=full -Wl,--lto-O3 -Wl,--icf=all -Wl,--gc-sections"

        ../configure --prefix=/opt/qemu-optimized --target-list=x86_64-softmmu \
            --enable-tcg --enable-slirp --enable-gtk --enable-sdl --enable-spice --enable-lto --enable-coroutine-pool \
            --disable-debug-info --disable-malloc-trim --disable-plugins --disable-docs --disable-werror --disable-fdt \
            CC="$CC" CXX="$CXX" LD="$LD" CFLAGS="$CFLAGS" CXXFLAGS="$CXXFLAGS" LDFLAGS="$LDFLAGS"

        ninja -j"$(nproc)" && sudo ninja install
        rm -rf /tmp/qemu-src
        deactivate

        if ! grep -q "/opt/qemu-optimized/bin" ~/.bashrc 2>/dev/null; then
            echo 'export PATH="/opt/qemu-optimized/bin:$PATH"' >> ~/.bashrc
        fi
        export PATH="/opt/qemu-optimized/bin:$PATH"

        if [[ -f ~/.zshrc ]]; then
            echo 'export PATH="/opt/qemu-optimized/bin:$PATH"' >> ~/.zshrc
        fi

        echo "✅ QEMU 10.1.2 built successfully!"
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
cpu_model="max,model-id=\"$cpu_host\""

read -rp "⚙ CPU core (default 2): " cpu_core
cpu_core="${cpu_core:-2}"

read -rp "💾 RAM GB (default 4): " ram_size
ram_size="${ram_size:-4}"

echo "💻 Khởi động VM..."

start_cmd="qemu-system-x86_64 \
    -machine type=q35 \
    -cpu $cpu_model \
    -smp $cpu_core \
    -m ${ram_size}G \
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
    -name \"$WIN_NAME VM\" \
    -daemonize \
    > /dev/null 2>&1"

eval "$start_cmd"

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

echo "✅ VM đã chạy với lệnh tối ưu!"
