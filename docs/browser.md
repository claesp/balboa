# Firefox browser

The workstation and laptop install the official Rocky Linux Firefox package.
DNF updates the package from the Rocky repositories.
The project applies locked privacy policies to every Firefox profile.

Telemetry is usage and diagnostic data.
The browser policies disable telemetry upload, local telemetry archives, and Firefox studies.
They also disable sponsored shortcuts, recommended stories, promotional messages, and remote search suggestions.

The policies disable automatic crash report submission and the legacy Pocket integration.
They retain malware and phishing protection.
The package remains the official Firefox build with a restricted configuration.

## Policy file

The source policy is `guest/firefox-policies.json`.
The renderer embeds it into desktop Kickstart files at `/etc/firefox/policies/policies.json`.
The installer sets mode `0755` on the directory.
The installer gives root ownership and mode `0644` to the file.

Locked preferences prevent ordinary users from enabling the disabled features through Firefox preferences.
The `DisableAppUpdate` policy disables the separate browser updater.
System package updates still update Firefox through the official repositories.

The server does not install Firefox or the browser policy.
Existing ISOs and installed machines retain their previous software and configuration.
For a new installation with these changes, render a new Kickstart.
Build a new ISO from that Kickstart.

## Examine a browser

1. Open Firefox on the installed laptop or workstation.
2. Enter `about:policies` in the address bar.
3. Make sure that the Active page contains the project policies.
4. Make sure that the Errors page contains no policy errors.

Open `about:preferences#privacy` to examine the enforced privacy configuration.
Use DNF for Firefox package updates.
See [Desktop package updates](updates.md) for security advisories and automatic updates.
Repeat the security assessment after approved system changes through [Maintenance](maintenance.md).

## Tests and references

The disposable container test starts Firefox with a separate temporary profile.
Marionette is the browser automation interface for the test.
The test uses a local connection.
It sends browser requests to a proxy that cannot respond.

The test requires Firefox to accept the complete policy file.
It reads the effective preferences and requires disabled privacy features to remain locked.
It also requires malware and phishing protection to remain enabled.

Mozilla documents the path for the system policy. [System policy path](https://support.mozilla.org/en-US/kb/customizing-firefox-using-policiesjson)
Mozilla lists the supported controls. [Policy reference](https://firefox-admin-docs.mozilla.org/reference/policies/)
The Marionette protocol defines the connection that the test uses. [Marionette protocol](https://firefox-source-docs.mozilla.org/remote/marionette/Protocol.html)
