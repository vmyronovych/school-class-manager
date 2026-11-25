# Evaluate the Vagrant DSL without VirtualBox, creating only temporary files.
# This verifies guards/machine scope; it does not boot or test a provider.
require 'json'
require 'tmpdir'
require 'digest'
module Vagrant
  class DSL
    def vm; self; end
    def trigger; self; end
    def define(name, **_options)
      Vagrant.machines << name
      yield DSL.new
    end
    def provider(*_args); yield DSL.new; end
    def before(*_args); yield DSL.new; end
    def ruby; end # Deliberately do not execute destructive lifecycle hooks.
    def method_missing(*_args); end
  end
  class << self
    attr_accessor :machines
    def require_version(value); raise 'Unexpected version pin' unless value == '= 2.4.9'; end
    def configure(_version); yield DSL.new; end
  end
end
source = File.expand_path('../Vagrantfile', __dir__)
example = JSON.parse(File.read(File.expand_path('../config.example.json', __dir__)))
Dir.mktmpdir('classroom-config-test') do |tmp|
  disk = File.join(tmp, 'dummy-state.vdi'); File.write(disk, '')
  path = File.join(tmp, 'config.json'); ENV['CLASSROOM_CONFIG'] = path
  check = lambda do |c, names, error=nil|
    File.write(path, JSON.generate(c)); Vagrant.machines = []
    begin
      load source
      raise 'Expected refusal was absent' if error
      raise "Unexpected machine scope: #{Vagrant.machines}" unless Vagrant.machines == names
    rescue RuntimeError => e
      raise unless error && e.message.include?(error)
    end
  end
  c = example.merge('state_disk'=>disk)
  check.call(c, ['server'])
  iso = File.join(tmp, 'dummy-windows.iso'); File.write(iso, 'test')
  check.call(c.merge('pupil_iso'=>iso, 'pupil_iso_sha256'=>Digest::SHA256.file(iso).hexdigest), ['server','pupil'])
  check.call(c.merge('mode'=>'lan'), [], 'Confirm domain/addressing')
  check.call(c.merge('realm'=>'AD.SCHOOL.EXAMPLE'), [], 'Lab realm must end')
  check.call(c.merge('domain'=>'bad domain'), [], 'Invalid NetBIOS')
  check.call(c.merge('state_disk'=>File.join(File.dirname(source), 'inside.vdi')), [], 'outside checkout')
  check.call(c.merge('state_disk'=>File.join(tmp, 'missing.vdi')), [], 'Create external disk')
  check.call(c.merge('pupil_iso'=>iso, 'pupil_iso_sha256'=>'bad'), [], 'checksum mismatch')
  check.call(c.merge('mode'=>'recovery', 'realm'=>'AD.SCHOOL.EXAMPLE'), ['server'])
  check.call(c.merge('mode'=>'lan', 'confirmed'=>true, 'gateway'=>'192.168.77.1'), ['server'])
end
puts 'PASS: 10 Vagrant configuration/scope cases; only server and one optional pupil'
