############################################################################
# Copyright (C) 2024 gempa GmbH                                            #
#                                                                          #
# All Rights Reserved.                                                     #
#                                                                          #
# NOTICE: All information contained herein is, and remains                 #
# the property of gempa GmbH and its suppliers, if any. The intellectual   #
# and technical concepts contained herein are proprietary to gempa GmbH    #
# and its suppliers.                                                       #
# Dissemination of this information or reproduction of this material       #
# is strictly forbidden unless prior written permission is obtained        #
# from gempa GmbH.                                                         #
############################################################################


import textwrap

from lib.config import CONFIG_OPTIONS
from lib.utils import getTerminalColumns

from lib.const import (
    LICENSES,
    SEISCOMP,
    BASE_PUBLIC_URL,
    DEFAULT_RELEASE,
    DEFAULT_ARCH,
    GSM,
    GSM_CONF,
)


class HelpFunction:
    def __init__(self):
        self.commandsDescriptions = {
            "search": "Search the package list for a regex pattern",
            "install [module1 ...]": "Install or update packages. To install a specific"
            " package run, e.g., install gds=2019.287. If no module is provided, all"
            " installed modules will be updated.",
            f"install {LICENSES} [module1 ...]": f"Install or update {LICENSES}. If no module"
            f" is provided, the {LICENSES} of all installed modules will be updated.",
            "localinstall [file1 ...]": "Install packages from local file (e.g.,"
            " scanloc-2023.128-seiscomp-5-rhel-8-x86_64.tar.gz). Note: The package"
            " description file is expected in the current directory. Use '-f' to install"
            " a version older than the installed one.",
            "reinstall [module1 ...]": "Reinstall packages. If no module is provided, all"
            " installed modules will be reinstalled.",
            f"reinstall {LICENSES} [module1 ...]": f"Install the {LICENSES} of installed"
            f" modules again. If no module is provided, the {LICENSES} of all installed"
            " modules will be installed.",
            "do-release-upgrade [--to=release]": f"Upgrade {SEISCOMP} release",
            "do-release-downgrade [--to=release]": f"Downgrade {SEISCOMP} release (only >= {SEISCOMP} 4)",
            "switch-os [--to=os/version[/arch]]": "Change the operating system",
            "hold [module1 ...]": "Add packages to hold",
            "hold files [file1 ...]": "Add files to hold  (expert only!)",
            "unhold [module1 ...]": "Remove packages from hold",
            "unhold files [file1 ...]": "Remove files from hold",
            "show": "Show available modules",
            "show updates": "Show possible updates",
            "show [module]": "Show latest package for a single module",
            "show changelog [module]": "Show module changelog (online)",
            "show history [module]": "Show a module’s install, uninstall, and update history",
            "show releases [distribution]": f"Show available {SEISCOMP} releases" \
                " for a distribution, [all] for all operating system",
            "show hold": "Show all hold packages",
            "show all [module1 ...]": "Show all available packages",
            "show own": "Show all packages available in your own repo (not availible in"
            " offline mode)",
            "show public": "Show all public packages",
            "info": "Show installed modules",
            "info [module1 ...]": "Show detailed information about an installed module",
            "info short": "Show installed modules (only package names)",
            "info deps [module1 ...]": "Show all available dependencies (only installed modules)",
            "check signature [module1 ...]": "Checks the gpg signature for a package(s)",
            "setup [options]": "Run initial setup interactively, or non-interactively with 'setup -y'. Run setup '-h' for listing available options.",
            "update": "Synchronize the package index from their source and show possible updates",
            "sync": "Synchronize the package index from their source",
            "migrate": "Updates config schema",
            "alias create [name]": "Create a alias",
            "alias remove [name]": "Remove a alias",
            "remove module1 [module2 ...]": "Uninstall packages",
            "clean [dbcache] [packages] [backup] [restore] [all]": "Clean up folders; target is one of:\n"
            "dbcache (sync), packages (downloads), backup, restore (temp files for release up/downgrade), or all (dbcache + packages)",
            "print nagios crontab": "Print GSM Nagios crontab entry",
            "print nagios output": "Print nagios output",
            "print nagios licenses": "Print nagios output for the licenses of the"
            " installed packages (expired or ending within license_info_days)",
            "print env": "Print the shell tab-completion setup hint"
        }
        self.commandsDescriptions = dict(
            sorted(
                self.commandsDescriptions.items(),
                key=lambda entry: self.commandSortKey(entry[0]),
            )
        )
        self.optionsDescriptions = [
            ("-c, --config", f"Load the configuration for {GSM} from the given file"),
            ("    --url", f"URL of the package directory, e.g., {BASE_PUBLIC_URL}"),
            ("    --noverify", "Do not verify server certificate"),
            ("-d, --downloadonly", "Do not install, just download"),
            ("    --downloaddir=directory", "Specifies an alternative directory to store packages"),
            ("    --installpath=directory", f"Full {SEISCOMP} installation path (setup)"),
            ("    --datadir=directory", f"{SEISCOMP} data directory (setup)"),
            ("-u, --user", "Username to use"),
            ("-p, --password", "Password to use"),
            ("-r, --release", f"{SEISCOMP} release, e.g., {DEFAULT_RELEASE}"),
            ("    --arch", f"System architecture, e.g., {DEFAULT_ARCH}"),
            ("    --os", "Operating system, e.g., ubuntu (auto-detected if omitted)"),
            ("    --osversion", "Operating system version, e.g., 24.04 (auto-detected)"),
            ("    --showurls", "Display URLs"),
            ("    --gpgverify", "Verify downloaded packages with gnupg (setup)"),
            ("    --backup", "Back up package files before installation (setup)"),
            ("    --backupdir=directory", "Directory for package backups, used with --backup"),
            ("    --licenseinfodays=N", "Days before the license-expiry notice is shown (setup)"),
            ("-y, --assumeyes", "Assume that the answer to questions which would be asked"
                " is yes. Errors still require user interaction. do-release-upgrade,"
                " do-release-downgrade and switch-os ask for confirmation even with -y."
                " With 'setup' this runs a"
                " non-interactive setup from the command-line parameters instead of"
                " prompting.\n"
                "Configuration Option: assumeyes"),
            ("    --exclude=[module1,...]", "Exclude packages from (re)install and remove"),
            ("-o, --offline", f"Run {GSM} in offline modus"),
            ("-f, --force", "Disables the remote file time check when downloading files."
                " With this option enabled file downloads are always performed. With"
                " 'install package=version' and 'localinstall' it also allows installing a"
                " package version older than the installed one (downgrade)."),
            ("    --debug", f"Run {GSM} in debug modus"),
            ("-V  --version", f"Show {GSM} version information"),
            ("-h, --help [section] [subsection] [config]", "Display this help message and exit\n"
                "section [commands or options or examples or full]\n"
                "subsection only commands [install or info or ...]\n"
                f"config: Configuration options for {GSM}.conf"),
        ]
        self.optionsDescriptions.sort(
            key=lambda entry: self.optionSortKey(entry[0])
        )
        self.setupInfo = (
            f"Create the {GSM} configuration. Without -y the setup runs interactively"
            " and prompts for each value. With -y it runs non-interactively and takes"
            " every value from the command-line parameters, falling back to detected"
            " or default values. The optional ~/.local/bin link is skipped."
        )
        self.setupRepositoryDescriptions = [
            ("no --user/--password", f"Public repository ({BASE_PUBLIC_URL})"),
            ("--user/--password", "Private repository; --url is then required"),
        ]
        self.setupOptionsDescriptions = [
            ("-r, --release=REL", f"{SEISCOMP} release, e.g., {DEFAULT_RELEASE}"),
            ("    --os=NAME", "Operating system (auto-detected if omitted)"),
            ("    --osversion=VER", "Operating system version (auto-detected)"),
            ("    --arch=ARCH", f"System architecture, e.g., {DEFAULT_ARCH}"),
            ("    --url=URL", "Repository base URL (required with credentials)"),
            ("-u, --user=USER", "Repository user"),
            ("-p, --password=PW", "Repository password"),
            ("    --installpath=DIR", f"Full {SEISCOMP} installation path"),
            ("    --downloaddir=DIR", "Package download directory"),
            ("    --datadir=DIR", f"{SEISCOMP} data directory"),
            ("    --gpgverify", "Verify downloaded packages with gnupg"),
            ("    --backup", "Back up package files before installation"),
            ("    --backupdir=DIR", "Directory for package backups"),
            (
                "    --licenseinfodays=N",
                "Days before the license-expiry notice is shown",
            ),
            ("-o, --offline", "Skip all online checks and take the values as-is"),
            ("    --noverify", "Do not verify the server certificate"),
        ]
        self.commandLineInfo = (
            f"{GSM} - gempa software manager is a command"
            " line tool for handling packages\n"
            f"Usage: {GSM} [options] command [module1] [module2] ..."
        )

    def commandNames(self):
        return sorted(entry.split()[0] for entry in self.commandsDescriptions)

    @staticmethod
    def commandSortKey(command):
        return [word for word in command.split() if not word.startswith(("[", "-"))]

    @staticmethod
    def optionSortKey(flags):
        names = [flag.strip(",") for flag in flags.split() if flag.startswith("-")]
        longName = next((name for name in names if name.startswith("--")), names[0])
        return longName.lstrip("-").split("=")[0]

    @staticmethod
    def wrapText(text, width=None):
        return "\n".join(
            textwrap.wrap(
                text,
                width=width or max(40, getTerminalColumns()),
                break_long_words=False,
                break_on_hyphens=False,
            )
        )

    @staticmethod
    def entryRenderer(keyColWidth=35, leftIndent=4, gap=3, minDescWidth=20):
        descWidth = max(
            minDescWidth, getTerminalColumns() - leftIndent - keyColWidth - gap
        )

        def wrapKey(key):
            lead = len(key) - len(key.lstrip(" "))
            stripped = key.strip()
            bracket = stripped.find("[")
            if bracket != -1:
                hangWidth = bracket
            else:
                space = stripped.find(" ")
                hangWidth = space + 1 if space != -1 else 0
            lines = textwrap.wrap(
                stripped,
                width=keyColWidth - lead,
                break_long_words=False,
                break_on_hyphens=False,
                subsequent_indent=" " * hangWidth,
            )
            return [" " * lead + line for line in (lines or [""])]

        def wrapDesc(description):
            lines = []
            for paragraph in description.split("\n"):
                lines.extend(
                    textwrap.wrap(
                        paragraph,
                        width=descWidth,
                        break_long_words=False,
                        break_on_hyphens=False,
                    )
                    or [""]
                )
            return lines

        def renderEntry(key, description):
            keyLines = wrapKey(key)
            descLines = wrapDesc(description)
            rows = []
            for i in range(max(len(keyLines), len(descLines))):
                keyPart = keyLines[i] if i < len(keyLines) else ""
                descPart = descLines[i] if i < len(descLines) else ""
                if descPart:
                    rows.append(
                        f"{' ' * leftIndent}{keyPart.ljust(keyColWidth)}{' ' * gap}{descPart}"
                    )
                else:
                    rows.append(f"{' ' * leftIndent}{keyPart}".rstrip())
            return "\n" + "\n".join(rows)

        return renderEntry

    def showHelp(
        self, commands=False, options=False, examples=False, showCommandsSection=None
    ):
        USAGE_INFO = f"""
{self.commandLineInfo}

Commands:"""

        renderEntry = self.entryRenderer()

        for command, description in self.commandsDescriptions.items():
            USAGE_INFO += renderEntry(command, description)

        USAGE_INFO += "\n\nOptions:"
        for flag, description in self.optionsDescriptions:
            USAGE_INFO += renderEntry(flag, description)

        USAGE_INFO += f"""
Examples:

* Workflow for installing the latest scanloc package from scratch:
  1. Set up the initial configuration (required when using for the first time)
  2. Synchronize the package index
  3. View the changelog of the package
  4. Install the latest scanloc package

  {GSM} setup (Run initial setup (required when using for the first time))
  {GSM} update
  seiscomp stop scanloc
  {GSM} show scanloc changelog
  {GSM} install scanloc
  seiscomp start scanloc

* Workflow for updating {SEISCOMP}, updating all other packages is therefore required:
  1. Set up the initial configuration
  2. Synchronize the package index
  3. Stop all modules
  4. Read the changelog of all packages, replace "<package>" by the name of the package.
  5. Install all packages
  6. Restart all packages

  {GSM} setup
  {GSM} update
  seiscomp stop
  {GSM} show
  {GSM} show <package> changelog
  {GSM} install
  seiscomp update-config   (updating the database tables may be required before,
                            read the {SEISCOMP} changelog)
  seiscomp start
"""

        if not (commands or options or examples):
            print(USAGE_INFO)
            return True

        if not examples:
            print(f"\n{self.commandLineInfo}\n")

        if commands:
            if showCommandsSection:
                showCommandsSection[:] = list(dict.fromkeys(showCommandsSection))
                failed = []
                print("Commands:")
                for command in showCommandsSection:
                    result = [
                        item
                        for item in self.commandsDescriptions
                        if item.startswith(command)
                    ]
                    if result:
                        for x in result:
                            print(renderEntry(x, self.commandsDescriptions[x]).lstrip("\n"))
                    else:
                        failed.append(command)
                if failed:
                    print(f"\nNo section found for: {', '.join(failed)}")
            else:
                commandsSectionStart = USAGE_INFO.find("Commands:")
                optionsSectionStart = USAGE_INFO.find("Options:")
                if commandsSectionStart != -1:
                    if optionsSectionStart != -1:
                        commandsSection = USAGE_INFO[
                            commandsSectionStart:optionsSectionStart
                        ]
                    else:
                        commandsSection = USAGE_INFO[commandsSectionStart:]
                    print(commandsSection)

        if options:
            optionsSectionStart = USAGE_INFO.find("Options:")
            examplesSectionStart = USAGE_INFO.find("Examples:")
            if optionsSectionStart != -1:
                if examplesSectionStart != -1:
                    optionsSection = USAGE_INFO[
                        optionsSectionStart:examplesSectionStart
                    ]
                else:
                    optionsSection = USAGE_INFO[optionsSectionStart:]
                print(optionsSection)
            else:
                print("Options section not found in USAGE_INFO")

        if examples:
            examplesSectionStart = USAGE_INFO.find("Examples:")
            if examplesSectionStart != -1:
                examplesSection = USAGE_INFO[examplesSectionStart:]
                print(examplesSection)
            else:
                print("Examples section not found in USAGE_INFO")

        return True

    def showSetupHelp(self):
        privateExample = f"{BASE_PUBLIC_URL.rsplit('/', 1)[0]}/ACME"
        renderEntry = self.entryRenderer(keyColWidth=24)

        SETUP_INFO = f"""
Usage: {GSM} setup [options]

{self.wrapText(self.setupInfo)}

Repository:"""
        for key, description in self.setupRepositoryDescriptions:
            SETUP_INFO += renderEntry(key, description)

        SETUP_INFO += "\n\nSetup options:"
        for flag, description in self.setupOptionsDescriptions:
            SETUP_INFO += renderEntry(flag, description)

        SETUP_INFO += f"""

Examples:
    # public repository, OS and architecture auto-detected
    {GSM} setup -y

    # private repository
    {GSM} setup -y --user ACME --password secret \\
        --url {privateExample} \\
        --release {DEFAULT_RELEASE} --installpath ~/seiscomp --datadir /home/data

    # offline: take everything as given, no server checks
    {GSM} setup -y -o --user ACME --password secret --url {privateExample}
"""
        print(SETUP_INFO)

        return True

    def showConfigInfo(self):
        renderEntry = self.entryRenderer(keyColWidth=45, gap=0)

        CONFIG_INFO = (
            "\nConfiguration options that you can additionally set in"
            f" {GSM_CONF}:\n"
        )
        for opt in CONFIG_OPTIONS:
            if opt.help:
                CONFIG_INFO += renderEntry(
                    f"{opt.key} = {opt.placeholder}", opt.help
                )

        print(f"{CONFIG_INFO}\n")

        return True

    @staticmethod
    def isSetupHelp(topic):
        return topic[:1] == ["setup"]

    def printHelp(self, topic):
        if self.isSetupHelp(topic):
            return self.showSetupHelp()

        section = topic[0] if topic else None
        subsections = topic[1:]

        if section == "config":
            return self.showConfigInfo()
        if section == "options":
            self.showHelp(options=True)
        elif section == "examples":
            self.showHelp(examples=True)
        elif section == "commands":
            self.showHelp(
                commands=True,
                showCommandsSection=subsections if subsections else None,
            )
        elif section == "full":
            self.showHelp()
        else:
            self.showHelp(options=True, commands=True)
        return True
