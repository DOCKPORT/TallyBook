# Use Ubuntu 22.04 for maximum AppImage compatibility (GLIBC 2.35)
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    binutils \
    libfuse2 \
    wget \
    file \
    # PySide6 system dependencies
    libxcb-cursor0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-randr0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libglib2.0-0 \
    libnss3 \
    libasound2 \
    libgl1-mesa-glx \
    # GTK integration and AppStream tools
    libharfbuzz0b \
    libgtk-3-0 \
    appstream \
    # Rust build dependencies (for native modules)
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /build

# Copy requirements.txt and install Python packages (including maturin)
COPY requirements.txt .
RUN pip3 install --no-cache-dir PyInstaller
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir maturin

# Copy all Rust modules and build each crate
COPY rust_modules/ /build/rust_modules/
RUN for crate in balance_compute calc_engine; do \
        cd /build/rust_modules/$crate && \
        rm -f target/wheels/*.whl && \
        maturin build --release && \
        pip3 install --no-cache-dir target/wheels/$crate-*.whl; \
    done

# Copy the AppStream metainfo template (will be processed during build)
COPY io.github.dockport.TallyBook.metainfo.xml.in .

# Copy the build script
COPY scripts/build_appimage_internal.sh /usr/local/bin/build_appimage.sh
RUN chmod +x /usr/local/bin/build_appimage.sh

CMD ["/usr/local/bin/build_appimage.sh"]