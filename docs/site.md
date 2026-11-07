# Site configuration

The site file supplies values for each production installation.
Keep the file outside version control with mode `0600`.
The renderer rejects unknown fields and unsafe field contents.

The required fields appear in `examples/site.json`.
The build procedure describes their password and key formats.
See [Build and installation](build.md) before you create production media.

## Root console recovery

The optional `root_password_hash` field accepts a SHA512 crypt password digest.
The digest uses the same format as `password_hash`.
Use a separate root password and retain it in the site recovery vault.

Without this field, the installer locks the root account.
The selected CIS profile reports a finding for that locked account.
The project does not silently exclude this rule.

The root password permits local console recovery.
SSH root login remains disabled.
The installer starts password aging from the installation date.
Account passwords expire after 90 days.

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
Use mode `0644` for public certificates and mode `0600` for the root-owned private key.

The service uses `LoadCredential` to read the private key with its restricted service identity.
Production media never embeds private TLS key contents through these fields.
The lab procedure embeds only disposable test keys.

If the receiver requires no client certificate, omit both client fields.
Without a trusted certificate path, the service uses the installed system CA collection.
The selected receiver must still authenticate through a valid certificate.

The installer enables upload only when the site supplies this object.
Without this object, the security assessment reports the selected upload control as a finding.
The receiver service and socket remain masked on each installed system.

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

## References

The review date is November 8, 2026.

- [Journal upload configuration](https://www.freedesktop.org/software/systemd/man/latest/journal-upload.conf.html)
- [Service credentials](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#Credentials)
