# Firefox browser

The workstation and laptop install the official Rocky Linux Firefox package.
The package receives security updates through Rocky repositories and GNOME Software or DNF.
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
The installed directory uses mode `0755`, and the file uses mode `0644` with root ownership.

Locked preferences prevent ordinary users from enabling the disabled features through Firefox preferences.
The `DisableAppUpdate` policy disables the separate browser updater.
System package updates still update Firefox through the official repositories.

The server does not install Firefox or the browser policy.
Existing ISOs and installed machines retain their previous software and configuration.
Render a new Kickstart and rebuild the ISO for a new installation with these changes.

## Examine a browser

On the installed laptop or workstation, open Firefox.
Enter `about:policies` in the address bar.
Make sure that the Active page contains the project policies.
Make sure that the Errors page contains no policy errors.

Open `about:preferences#privacy` to examine the enforced privacy configuration.
Use GNOME Software or DNF for Firefox package updates.
Repeat the security assessment after approved system changes through [Maintenance](maintenance.md).

## Tests and references

The disposable container test starts Firefox with a separate temporary profile.
Marionette is the browser automation interface for the test.
The test uses a local connection and directs browser web requests to a dead proxy.

The test requires Firefox to accept the complete policy file.
It reads the effective preferences and requires disabled privacy features to remain locked.
It also requires malware and phishing protection to remain enabled.

Mozilla documents the [system policy path](https://support.mozilla.org/en-US/kb/customizing-firefox-using-policiesjson).
Its [policy reference](https://firefox-admin-docs.mozilla.org/reference/policies/) describes the supported controls.
The [Marionette protocol](https://firefox-source-docs.mozilla.org/remote/marionette/Protocol.html) describes the test connection.
