# Site configuration

The site file supplies values for each production installation.
Keep the file outside version control with mode `0600`.
The renderer rejects unknown fields and unsafe field contents.

The required fields appear in `examples/site.json`.
The build procedure describes their password and key formats.
See [Build and installation](build.md) before you create production media.

## Root console recovery

The required `root_password_hash` field accepts a SHA512 crypt password digest.
The digest uses the same format as `password_hash`.
Retain the root password in the site recovery vault.

The renderer rejects a missing or malformed digest.
The root console and administrator password fields can contain the same digest.

The root password permits local console recovery.
SSH root login remains disabled.
The installer starts password aging from the installation date.
Account passwords expire after 90 days.

## Keyboard and language

An XKB layout defines the keyboard keys.
The `keyboard` field requires a supported XKB layout identifier.
The renderer uses that value in `keyboard --xlayouts` in Kickstart.

Use `se` for Swedish or `us` for US English.
The value `sv` is a language code and is not a keyboard layout.
The console keymap name `se-latin1` is not an XKB layout identifier.

A locale selects language and regional text formats.
The `language` field selects the locale independently from the keyboard layout.
For a Swedish keyboard and Swedish language, use these site fields:

```json
"keyboard": "se",
"language": "sv_SE.UTF-8"
```

The supported layout names appear in [the keyboard catalog](../data/keyboards.json).
The catalog records layouts from the official Rocky Linux `xkeyboard-config` package.
The renderer and ISO preflight tests reject names outside that catalog.

## Disk encryption

The account and bootloader digest fields do not configure the LUKS passphrase.
Without an explicit installation key, the installer prompts for this passphrase.
For unattended installation, set the optional `luks_passphrase` field in the site JSON file.

The field contains the actual plaintext passphrase, with 5 to 128 printable characters and no line breaks.
It differs from `bootloader_password_hash`, which protects GRUB commands.
The renderer embeds the passphrase in the generated Kickstart and ISO.

Use mode `0600` for a site file that contains this field.
The renderer rejects group or other access to a site file that contains a LUKS passphrase.
Omit the field or use `null` to request interactive installation entry.
Use [Unattended disk encryption](build.md#unattended-disk-encryption) for the build procedure.

## Image text

The optional `branding_text` field supplies the text below the generated logo.
The default value is `Balboa`.
The field accepts 1 to 64 printable characters without line breaks.

The render flag `--branding-text` overrides the site value.
The same text appears in all three images.
See [Boot and desktop images](branding.md) for image generation and installation.


## Central journal receiver

A journal receiver accepts structured system log events.
TLS encrypts network traffic and authenticates certificates.
The optional `journal_upload` object supplies an HTTPS receiver address and certificate paths.

Add this object to the site file for an authenticated journal receiver:

```json
"journal_upload": {
  "url": "https://logs.example.test:19532",
  "trusted_certificate_file": "/etc/pki/balboa/ca.pem",
  "client_certificate_file": "/etc/pki/balboa/client.pem",
  "client_key_file": "/etc/pki/balboa/client.key"
}
```

Replace the example address with the site receiver address.
Use a receiver that accepts the systemd journal upload protocol.
The renderer rejects HTTP, URL credentials, and certificate paths outside `/etc/pki/`.

The certificate fields contain paths, not certificate contents.
Provision the certificates and private key through the approved site procedure before the first boot.
Use mode `0644` for public certificates.
Give the private key root ownership, group `balboa-logs`, and mode `0640`.
Use mode `0755` for directories that contain public certificates.

If the site file names a client key, the installer creates the `balboa-logs` group.
Only the journal upload service receives this group through its service definition.
Do not add interactive users to this group.
The native assessment requires the specified key ownership and access mode.

The service reads the key with its restricted identity and the normal certificate SELinux label.
Rocky policy blocks this service from reading the default systemd credential label.
The project keeps SELinux enforcing and uses the restricted group instead.

For the example paths, apply the key access and SELinux labels at the installed system console.

```sh
sudo chown root:balboa-logs /etc/pki/balboa/client.key
sudo chmod 0640 /etc/pki/balboa/client.key
sudo chmod 0755 /etc/pki/balboa
sudo chmod 0644 /etc/pki/balboa/ca.pem /etc/pki/balboa/client.pem
sudo restorecon -RF /etc/pki/balboa
```
Production media never embeds private TLS key contents through these fields.
The lab procedure embeds only disposable test keys.

If the receiver requires no client certificate, omit both client fields.
Without a trusted certificate path, the service uses the installed system CA collection.
The selected receiver must still authenticate through a valid certificate.
For systemd 257, restrict the receiver to HTTP/1.1 to avoid the observed HTTP/2 upload buffer error.
This protocol restriction does not disable TLS.

The installer enables upload only when the site supplies this object.
Without this object, the security assessment reports the selected upload control as a finding.
The receiver service and socket remain masked on each installed system.

## Configuration at deployment

Production images can omit `journal_upload` until deployment.
The image contains no assumed receiver address or client key.
The security assessment requires completed logging configuration before release.

Use the local console for the following procedure.
The example uses client certificates and the standard paths from this document.

Create the group and configuration directories on the installed system:

```sh
getent group balboa-logs >/dev/null || sudo groupadd --system balboa-logs
sudo install -d -m 0755 /etc/pki/balboa /etc/systemd/journal-upload.conf.d /etc/systemd/system/systemd-journal-upload.service.d
sudoedit /etc/systemd/journal-upload.conf.d/60-balboa.conf
```

Put this content in the upload file.
Replace the example address with the deployment receiver address.

```ini
[Upload]
URL=https://logs.example.test:19532
TrustedCertificateFile=/etc/pki/balboa/ca.pem
ServerCertificateFile=/etc/pki/balboa/client.pem
ServerKeyFile=/etc/pki/balboa/client.key
```

Create the service file with this command:

```sh
sudoedit /etc/systemd/system/systemd-journal-upload.service.d/60-balboa-credentials.conf
```

Put this content in the service file:

```ini
[Service]
SupplementaryGroups=balboa-logs
```

Provision the CA certificate, client certificate, and private key through approved site storage.
Apply the access modes and SELinux labels from the preceding section.
Add the key path to the native policy through this command:

```sh
sudo python3 - <<'PY'
import json
from pathlib import Path
path = Path('/etc/balboa/native-policy.json')
policy = json.loads(path.read_text())
policy['journal_client_key'] = '/etc/pki/balboa/client.key'
path.write_text(json.dumps(policy, indent=2) + '\n')
path.chmod(0o600)
PY
sudo chmod 0644 /etc/systemd/journal-upload.conf.d/60-balboa.conf /etc/systemd/system/systemd-journal-upload.service.d/60-balboa-credentials.conf
sudo restorecon -RF /etc/pki/balboa /etc/systemd /etc/balboa
sudo systemctl daemon-reload
sudo systemctl enable systemd-journal-upload.service
```

Do the delivery test and repeat remediation through the following procedure.

## Delivery test

Operate these commands at the installed system console after certificate provisioning.

```sh
sudo systemctl restart systemd-journal-upload.service
sudo systemctl status systemd-journal-upload.service
sudo journalctl -u systemd-journal-upload.service
logger 'Balboa central logging delivery test'
```

Make sure that the receiver retains the test event.
Make sure that the certificate renewal procedure operates before certificate expiry.
After corrections, repeat the assessment through [Security policy](security.md).

If the first remediation failed because certificates were absent, restart remediation after certificate provisioning.
Use the local console because server SSH requires completed remediation.
The remediation service requests an automatic restart after success.

```sh
sudo systemctl reset-failed systemd-journal-upload.service balboa-harden.service
sudo systemctl restart systemd-journal-upload.service
sudo systemctl restart balboa-harden.service
```

## References

The review date is November 8, 2026.

- [Journal upload configuration](https://www.freedesktop.org/software/systemd/man/latest/journal-upload.conf.html)
- [Service credentials](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#Credentials)
- [Upstream upload buffer issue](https://github.com/systemd/systemd/issues/39166)
