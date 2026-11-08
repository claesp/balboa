"""Assess Firefox policies with an isolated headless browser and local Marionette."""

import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time


class Marionette:
    def __init__(self, client):
        self.client = client
        self.identifier = 0
        self.receive()

    def receive(self):
        length = b""
        while True:
            byte = self.client.recv(1)
            if not byte:
                raise RuntimeError("Firefox closed the test connection.")
            if byte == b":":
                break
            length += byte
        remaining = int(length)
        data = b""
        while remaining:
            block = self.client.recv(remaining)
            if not block:
                raise RuntimeError("Firefox returned an incomplete test response.")
            data += block
            remaining -= len(block)
        return json.loads(data)

    def command(self, name, parameters):
        self.identifier += 1
        data = json.dumps([0, self.identifier, name, parameters]).encode()
        self.client.sendall(str(len(data)).encode() + b":" + data)
        response = self.receive()
        if response[:2] != [1, self.identifier] or response[2] is not None:
            raise RuntimeError(f"Firefox rejected {name}: {response}")
        return response[3]


def main():
    expected = json.loads(Path("/etc/firefox/policies/policies.json").read_text())["policies"]
    with tempfile.TemporaryDirectory(prefix="balboa-firefox-") as directory:
        profile = Path(directory)
        preferences = {
            "marionette.port": 2828,
            "remote.prefs.recommended": False,
            "marionette.prefs.recommended": False,
            "network.proxy.type": 1,
            "network.proxy.http": "127.0.0.1",
            "network.proxy.http_port": 9,
            "network.proxy.ssl": "127.0.0.1",
            "network.proxy.ssl_port": 9,
            "network.proxy.no_proxies_on": "localhost,127.0.0.1",
        }
        (profile / "user.js").write_text("".join(
            f"user_pref({json.dumps(name)}, {json.dumps(value)});\n" for name, value in preferences.items()))
        with (profile / "firefox.log").open("w+") as log:
            process = subprocess.Popen([
                "firefox", "--headless", "--no-remote", "--marionette", "--remote-allow-system-access",
                "--profile", directory, "about:blank"], stdout=log, stderr=log,
                env={**os.environ, "MOZ_CRASHREPORTER_DISABLE": "1"})
            client = None
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        client = socket.create_connection(("127.0.0.1", 2828), timeout=1)
                        break
                    except OSError:
                        time.sleep(0.2)
                if client is None:
                    log.seek(0)
                    raise RuntimeError("Firefox did not start its local test interface.\n" + log.read()[-8000:])
                client.settimeout(30)
                browser = Marionette(client)
                browser.command("WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
                browser.command("Marionette:SetContext", {"value": "chrome"})
                result = browser.command("WebDriver:ExecuteScript", {"script": """
                    const names = [
                      "datareporting.healthreport.uploadEnabled",
                      "datareporting.policy.dataSubmissionEnabled",
                      "toolkit.telemetry.archive.enabled",
                      "browser.newtabpage.activity-stream.asrouter.userprefs.cfr.addons",
                      "browser.newtabpage.activity-stream.asrouter.userprefs.cfr.features",
                      "browser.search.suggest.enabled",
                      "browser.urlbar.suggest.quicksuggest.sponsored",
                      "browser.newtabpage.activity-stream.showSponsoredTopSites",
                      ...Object.keys(arguments[0].Preferences)
                    ];
                    const preferences = {};
                    for (const name of names) {
                      preferences[name] = {
                        value: Services.prefs.getBoolPref(name, true),
                        locked: Services.prefs.prefIsLocked(name)
                      };
                    }
                    return {version: Services.appinfo.version,
                      studiesAllowed: Services.policies.isAllowed("Shield"),
                      suggestConsentLocked: [
                        "browser.urlbar.quicksuggest.dataCollection.enabled",
                        "browser.urlbar.quicksuggest.online.enabled"
                      ].some(name => Services.prefs.prefIsLocked(name) &&
                        !Services.prefs.getBoolPref(name, true)),
                      active: Services.policies.getActivePolicies(), preferences,
                      malwareProtection: Services.prefs.getBoolPref("browser.safebrowsing.malware.enabled"),
                      phishingProtection: Services.prefs.getBoolPref("browser.safebrowsing.phishing.enabled")};
                    """, "args": [expected], "newSandbox": True})["value"]
                for name, value in expected.items():
                    if result["active"].get(name) != value:
                        raise RuntimeError(f"Firefox did not accept policy {name}: {result['active'].get(name)}")
                for name, value in result["preferences"].items():
                    if value != {"value": False, "locked": True}:
                        raise RuntimeError(f"Firefox did not disable and lock {name}: {value}")
                if not result["malwareProtection"] or not result["phishingProtection"]:
                    raise RuntimeError("Firefox security protection is disabled.")
                if result["studiesAllowed"]:
                    raise RuntimeError("Firefox studies remain enabled.")
                if not result["suggestConsentLocked"]:
                    raise RuntimeError("Firefox Suggest data sharing is not disabled and locked.")
                print(json.dumps(result, indent=2))
                print("The Firefox privacy policy assessment passed.")
            finally:
                if client is not None:
                    client.close()
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == "__main__":
    main()
