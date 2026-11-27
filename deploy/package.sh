#!/usr/bin/env bash
# Ubuntu build host: node, .NET SDK, wixl, python3, GNU tar/coreutils.
set -euo pipefail
cd "$(dirname "$0")/.."
arch=${1:-amd64}
case "$arch" in amd64) rid=linux-x64;; arm64) rid=linux-arm64;; *) exit 2;; esac
version=$(sed -n 's/.*<Version>\(.*\)<\/Version>.*/\1/p' Directory.Build.props)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
npm --prefix web ci
npm --prefix web run build
dotnet publish src/Scm.Api -c Release -r "$rid" --self-contained true -o "$work/panel"
dotnet publish src/Scm.Agent -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:DebugType=None -o "$work/agent"
mkdir -p out "$work/bundle"
cp deploy/windows/agent.wxs "$work/agent/"
msi="$work/bundle/ScmAgent-$version-x64.msi"
(cd "$work/agent" && wixl -a x64 -D Version="$version" -o "$msi" agent.wxs)
tar --format=ustar -C "$work/panel" -czf "$work/bundle/panel.tar.gz" .
cp -r deploy/server "$work/bundle/"
cp deploy/windows/Backup-SchoolVM.ps1 "$work/bundle/"
cp README.md LICENSE "$work/bundle/"
cp -r docs "$work/bundle/"
printf '%s\n' "$arch" > "$work/bundle/architecture"
printf '%s\n' "$version" > "$work/bundle/VERSION"
(cd "$work/bundle" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
tar --format=ustar -C "$work/bundle" -czf "out/scm-$version-$arch.tar.gz" .
(cd out && sha256sum "scm-$version-$arch.tar.gz" > "scm-$version-$arch.tar.gz.sha256")
