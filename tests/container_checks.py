"""Do tests that require Rocky Linux tooling."""

from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    subprocess.run(["ksvalidator", "-v", "RHEL10", sys.argv[1]], check=True)
    from pykickstart.parser import KickstartParser
    from pykickstart.version import makeVersion
    from balboa.render import validate_keyboard

    parser = KickstartParser(makeVersion("RHEL10"))
    parser.readKickstart(sys.argv[1])
    for layout in parser.handler.keyboard.x_layouts:
        validate_keyboard(layout)
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
        import argparse
        from balboa.dvd import catalog, dvd_device, extract_metadata, inventory
        from guest.install_files import payload_files
        arguments = argparse.ArgumentParser()
        arguments.add_argument('kickstart', type=Path)
        arguments.add_argument('--packages', action='store_true')
        arguments.add_argument('--dvd', type=Path, required=True)
        arguments.add_argument('--report', type=Path, required=True)
        options = arguments.parse_args()
        method = parser.handler.method
        if (method.method != 'harddrive' or method.partition != dvd_device() or method.dir != '/'
                or parser.handler.repo.repoList):
            raise ValueError('Installation must use only the DVD. Other package sources require review.')
        render_dir = options.kickstart.resolve().parent
        guest = Path('/workspace/guest')
        copier = render_dir / 'install_files.py'
        if not copier.is_file() or copier.is_symlink() or copier.read_bytes() != (guest / copier.name).read_bytes():
            raise ValueError('The Kickstart requires the current file installer. Render it again.')
        payload = render_dir / 'balboa-files'
        if not payload.is_dir():
            raise ValueError('The Kickstart requires balboa-files. Render it again.')
        files = dict(payload_files(payload))
        required = [('baseline.sh', '/usr/local/libexec/balboa/baseline.sh', True),
                    ('harden.sh', '/usr/local/libexec/balboa/harden.sh', True),
                    ('failure.sh', '/usr/local/libexec/balboa/failure.sh', True),
                    ('native_checks.py', '/usr/local/libexec/balboa/native_checks.py', True),
                    ('package_source.py', '/usr/local/libexec/balboa/package_source.py', True),
                    ('balboa-harden.service', '/etc/systemd/system/balboa-harden.service', False)]
        for name, destination, executable in required:
            path = Path(destination.lstrip('/'))
            mode = 0o755 if executable else 0o600
            if files.get(path) != mode or (payload / path).read_bytes() != (guest / name).read_bytes():
                raise ValueError('The Kickstart lacks the current initial package guard. Render it again.')
        with tempfile.TemporaryDirectory() as temporary, dnf.Base() as base:
            directory = Path(temporary) / 'dvd'
            extract_metadata(options.dvd, directory)
            record = catalog()
            if inventory(directory) != record['packages']:
                raise ValueError('The DVD package inventory differs from the reviewed catalog.')
            base.conf.cachedir = temporary
            base.conf.persistdir = temporary
            base.conf.logdir = temporary
            base.conf.install_weak_deps = False
            base.conf.excludepkgs = parser.handler.packages.excludedList
            for repository, directory in (("baseos", "BaseOS"), ("appstream", "AppStream")):
                base.repos.add_new_repo(repository, base.conf,
                                        baseurl=[f"file://{temporary}/dvd/{directory}/"])
            base.fill_sack(load_system_repo=False)
            base.read_comps()
            for package in parser.handler.packages.packageList:
                if not base.sack.query().available().filter(name=package):
                    raise ValueError(f"The locked DVD does not contain {package}. Review the package before inclusion.")
                base.install(package)
            environment = parser.handler.packages.environment
            if environment and not base.comps.environment_by_pattern(environment):
                raise ValueError(f"The locked DVD does not contain environment {environment}. Review it before inclusion.")
            for group in parser.handler.packages.groupList:
                if not base.comps.group_by_pattern(group.name):
                    raise ValueError(f"The locked DVD does not contain group {group.name}. Review it before inclusion.")
                base.group_install(group.name, ("mandatory",), exclude=parser.handler.packages.excludedList)
            base.resolve()
            selected = sorted('|'.join((p.name, str(p.epoch), p.version, p.release, p.arch))
                              for p in base.transaction.install_set)
            options.report.write_text(json.dumps({'dvd_sha256': record['dvd_sha256'],
                                                  'packages': selected, 'network': 'none'}, indent=2) + '\n')
            print(f"The minimal selection resolves to {len(base.transaction.install_set)} packages.")
        print("The selected packages and dependencies resolve from the locked DVD without network access.")
    print("Kickstart syntax, shell syntax, and Rocky CIS Level 2 profile tests passed.")


if __name__ == "__main__":
    main()
