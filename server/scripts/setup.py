#!/usr/bin/python3
"""Persistent storage bootstrap. Refuses ambiguous/partially initialized state."""
import json, pathlib, subprocess, ipaddress, os

def run(*args, **kw):
    return subprocess.run(args, check=True, text=True, **kw)

def main():
    c = json.loads(pathlib.Path('/etc/classroom/config.json').read_text())
    assert c['mode'] in ('lab', 'recovery', 'lan')
    if c['mode'] == 'lan':
        assert c['confirmed'] is True, 'Real network/domain confirmation required'
    net = ipaddress.IPv4Network(f"{c['ip']}/{c['netmask']}", strict=False)
    assert ipaddress.IPv4Address(c['ip']) not in (net.network_address, net.broadcast_address)
    root = pathlib.Path('/srv/classroom')
    root.mkdir(exist_ok=True)
    device = '/dev/sdb'
    assert pathlib.Path(device).exists(), 'Persistent SATA port-1 disk missing'
    disks = json.loads(run('lsblk', '-Jbo', 'NAME,SIZE,TYPE,MOUNTPOINTS', device, capture_output=True).stdout)['blockdevices']
    d = disks[0]
    assert d['type'] == 'disk' and not d.get('children'), 'Expected whole unpartitioned state VDI'
    assert int(d['size']) == int(c['state_disk_mb']) * 1024 * 1024, 'Unexpected disk size'
    fs = run('blkid', '-p', '-o', 'value', '-s', 'TYPE', device, capture_output=True).stdout.strip() if subprocess.run(['blkid', '-p', device], capture_output=True).returncode == 0 else ''
    if not fs:
        signatures = json.loads(run('wipefs', '--json', device, capture_output=True).stdout)['signatures']
        assert not signatures and c.get('initialize_storage') is True, 'Refusing format: disk not explicitly approved empty'
        run('mkfs.ext4', '-L', 'classroom-state', device)
    else:
        assert fs == 'ext4', 'Unexpected filesystem; will not format'
    uuid = run('blkid', '-s', 'UUID', '-o', 'value', device, capture_output=True).stdout.strip()
    fstab = pathlib.Path('/etc/fstab')
    lines = [l for l in fstab.read_text().splitlines() if '# classroom-managed' not in l]
    lines += [f'UUID={uuid} /srv/classroom ext4 defaults 0 2 # classroom-managed']
    fstab.write_text('\n'.join(lines) + '\n')
    if subprocess.run(['mountpoint', '-q', str(root)]).returncode:
        run('mount', str(root))
    identity = {k: c[k] for k in ('realm', 'domain', 'hostname', 'ip', 'netmask', 'mode')}
    meta = root / 'identity.json'
    if meta.exists():
        assert json.loads(meta.read_text()) == identity, 'Identity mismatch: do not silently rename/readdress an existing DC'
    else:
        assert not (root / 'domain').exists(), 'Unrecognized existing domain; recovery required'
        meta.write_text(json.dumps(identity, indent=2) + '\n')
    for name in ('state', 'etc', 'homes'):
        (root / name).mkdir(mode=0o700, exist_ok=True)
    state = pathlib.Path('/var/lib/samba')
    if subprocess.run(['mountpoint', '-q', str(state)]).returncode:
        # Fresh packages may contain empty infrastructure directories, never an AD DB.
        assert not (state / 'private/sam.ldb').exists(), 'Unexpected domain on disposable root'
        run('mount', '--bind', str(root / 'state'), str(state))
    lines += ['/srv/classroom/state /var/lib/samba none bind 0 0 # classroom-managed']
    fstab.write_text('\n'.join(lines) + '\n')
    smb = pathlib.Path('/etc/samba/smb.conf')
    if (root / 'etc/smb.conf').exists():
        if smb.is_symlink():
            assert smb.resolve() == root / 'etc/smb.conf'
        else:
            smb.unlink(missing_ok=True)
            smb.symlink_to(root / 'etc/smb.conf')
    # Stable second NIC selected by VirtualBox's predictable PCI slot.
    run('ip', 'link', 'show', 'enp0s8', stdout=subprocess.DEVNULL)
    network = f'''network:
  version: 2
  ethernets:
    enp0s8:
      dhcp4: false
      dhcp6: false
      addresses: [{c['ip']}/{net.prefixlen}]
'''
    # NAT remains the update/SSH default route. No LAN default route or host change.
    pathlib.Path('/etc/netplan/60-classroom.yaml').write_text(network)
    run('netplan', 'apply')
    if (root / 'domain-ready').exists():
        assert (root / 'domain/private/sam.ldb').exists(), 'Ready marker without AD DB; refusing empty rebuild'
        # DC DNS is used only inside guest; the host and router remain untouched.
        run('systemctl', 'disable', '--now', 'systemd-resolved')
        resolv = pathlib.Path('/etc/resolv.conf')
        resolv.unlink(missing_ok=True)
        resolv.write_text(f"nameserver {c['ip']}\nsearch {c['realm'].lower()}\n")
        signd = root / 'domain/ntp_signd'
        signd.mkdir(mode=0o750, exist_ok=True)
        run('chgrp', '_chrony', str(signd))
        signd.chmod(0o750)
        pathlib.Path('/etc/chrony/conf.d/classroom.conf').write_text(
            f'allow {net}\nntpsigndsocket {signd}\n')
        run('systemctl', 'restart', 'chrony')

if __name__ == '__main__':
    main()
