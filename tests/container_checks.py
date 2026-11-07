"""Do tests that require Rocky Linux tooling."""

from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def main():
    subprocess.run(["ksvalidator", "-v", "RHEL10", sys.argv[1]], check=True)
    for script in Path("/workspace/guest").glob("*.sh"):
        subprocess.run(["bash", "-n", str(script)], check=True)
    ds = Path("/usr/share/xml/scap/ssg/content/ssg-rl10-ds.xml")
    root = ET.parse(ds).getroot()
    ns = {"x": "http://checklists.nist.gov/xccdf/1.2"}
    for suffix, title in (("cis", "Level 2 - Server"), ("cis_workstation_l2", "Level 2 - Workstation")):
        profile = root.find(f".//x:Profile[@id='xccdf_org.ssgproject.content_profile_{suffix}']", ns)
        if profile is None or title not in profile.findtext("x:title", namespaces=ns):
            raise ValueError(f"The Rocky datastream does not contain {title}.")
    from balboa.policy import tailoring
    import json
    with tempfile.TemporaryDirectory() as temporary:
        for definition in Path("/workspace/flavors").glob("*.json"):
            profile_id, text = tailoring(definition.stem, json.loads(definition.read_text())["profile"])
            policy = Path(temporary) / "tailoring.xml"
            policy.write_text(text)
            subprocess.run(["oscap", "xccdf", "generate", "guide", "--profile", profile_id,
                            "--tailoring-file", str(policy), "--output", temporary + "/guide.html", str(ds)], check=True)
    if "--packages" in sys.argv:
        import dnf
        from pykickstart.parser import KickstartParser
        from pykickstart.version import makeVersion

        parser = KickstartParser(makeVersion("RHEL10"))
        parser.readKickstart(sys.argv[1])
        with tempfile.TemporaryDirectory() as temporary, dnf.Base() as base:
            base.conf.cachedir = temporary
            base.conf.persistdir = temporary
            base.conf.logdir = temporary
            base.conf.install_weak_deps = False
            base.conf.excludepkgs = parser.handler.packages.excludedList
            for repository, directory in (("baseos", "BaseOS"), ("appstream", "AppStream")):
                base.repos.add_new_repo(repository, base.conf,
                                        baseurl=[f"https://dl.rockylinux.org/pub/rocky/10/{directory}/x86_64/os/"])
            base.fill_sack(load_system_repo=False)
            base.read_comps()
            for package in parser.handler.packages.packageList:
                if not base.sack.query().available().filter(name=package):
                    raise ValueError(f"The official repositories do not contain {package}.")
                base.install(package)
            environment = parser.handler.packages.environment
            if environment and not base.comps.environment_by_pattern(environment):
                raise ValueError(f"The official repositories do not contain {environment}.")
            for group in parser.handler.packages.groupList:
                if not base.comps.group_by_pattern(group.name):
                    raise ValueError(f"The official repositories do not contain {group.name}.")
                base.group_install(group.name, ("mandatory",), exclude=parser.handler.packages.excludedList)
            base.resolve()
            print(f"The minimal selection resolves to {len(base.transaction.install_set)} packages.")
        print("The selected packages and dependencies resolve in the official repositories.")
    print("Kickstart syntax, shell syntax, and Rocky CIS Level 2 profile tests passed.")


if __name__ == "__main__":
    main()
