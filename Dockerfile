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
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements and install them
COPY requirements.txt .
RUN pip3 install --no-cache-dir PyInstaller
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Rust toolchain for building native modules (used at runtime with mounted source)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install maturin

# Copy the AppStream metainfo template (will be processed during build)
COPY io.github.dockport.TallyBook.metainfo.xml.in .

# Create a build script inside the container
RUN echo '#!/bin/bash\n\
set -e\n\
# Build native Rust modules (source is mounted at runtime)\n\
for crate in balance_compute calc_engine; do\n\
    cd /build/rust_modules/$crate\n\
    maturin build --release --find-interpreter\n\
    pip3 install /build/rust_modules/$crate/target/wheels/*.whl\n\
done\n\
# Build the binary\n\
cd /build && pyinstaller --noconfirm TallyBook.spec\n\
# Prepare AppDir\n\
mkdir -p TallyBook.AppDir/usr/bin\n\
mkdir -p TallyBook.AppDir/usr/share/metainfo\n\
cp dist/TallyBook TallyBook.AppDir/usr/bin/TallyBook\n\
# Extract version from version.py and generate AppStream metainfo\n\
APP_VERSION=$(grep ^APP_VERSION modules/version.py | cut -d\\" -f2)\n\
echo "Building AppStream metainfo for version $APP_VERSION ..."\n\
sed "s/@APP_VERSION@/$APP_VERSION/g" io.github.dockport.TallyBook.metainfo.xml.in \\\n\
    > TallyBook.AppDir/usr/share/metainfo/io.github.dockport.TallyBook.metainfo.xml\n\
# Validate the metainfo file\n\
appstream-util validate TallyBook.AppDir/usr/share/metainfo/io.github.dockport.TallyBook.metainfo.xml\n\
# Download appimagetool if not present\n\
if [ ! -f appimagetool ]; then\n\
    wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool\n\
    chmod +x appimagetool\n\
fi\n\
# Build AppImage (forcing type 2)\n\
ARCH=x86_64 ./appimagetool --appimage-extract-and-run TallyBook.AppDir\n\
' > /usr/local/bin/build_appimage.sh && chmod +x /usr/local/bin/build_appimage.sh

CMD ["/usr/local/bin/build_appimage.sh"]
