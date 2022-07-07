import dotbot
import os
import sys
import subprocess

class OmniPkg(dotbot.Plugin):
    # only support the omnipkg directive
    _mainDirective = "omnipkg"

    # omnipkg directive should include subdirectives underneath it as such
    _installSubDirective = "install"
    _updateSubDirective = "update"
    _upgradeSubDirective = "upgrade"

    # The name of the package manager that has been found
    _packageManagerName = ""

    # The name of the platform
    _platformName = ""

    # The lookup name in optional package dictionaries
    _dictLookup = ""
    _dictLookupElse = "else"

    # commands are setup based on the platform and installed package manager
    _installCommand = ""
    _updateCommand = ""
    _upgradeCommand = ""

    # Command used to check that the package exists before installing it
    _existsCheck = ""

    def __init__(self, context):
        super(OmniPkg, self).__init__(context)
        # here we setup the commands based on whether linux or macos is
        # installed.
        # if macos is installed then we try to setup with brew
        # if linux is installed then we select a package manager
        # and use that instead
        if sys.platform == "linux" or sys.platform == "linux2":
            self._setupLinux()
        elif sys.platform == "darwin":
            self._setupMacOS()

    def can_handle(self, directive):
        # only allow the directives listed above
        return directive in (self._mainDirective)

    def handle(self, directive, data):
        # first process the subdirectives then run each

        # for each item in data, identify the sub directive and get the data
        # for the sub directive
        _doUpdate = False
        _updateStatus = True

        _doUpgrade = False
        _upgradeStatus = True

        _installData = []
        _installStatus = True

        for sd in data:
            if isinstance(sd, str):
                if sd == self._updateSubDirective:
                    _doUpdate = True
                elif sd == self._upgradeSubDirective:
                    _doUpgrade = True
            elif isinstance(sd, object):
                if self._installSubDirective in sd:
                    _installData = sd[self._installSubDirective]

        # execute the processed sub directives and report any errors but
        # continue for each sub directive
        if _doUpdate:
            _updateStatus = self._doUpdate()
            if not _updateStatus:
                self._printSubDirectiveError(self._updateSubDirective)

        _installStatus = self._doInstall(_installData)
        if not _installStatus:
            self._printSubDirectiveError(self._installSubDirective)

        if _doUpgrade:
            _upgradeStatus = self._doUpgrade()
            if not _upgradeStatus:
                self._printSubDirectiveError(self._upgradeSubDirective)

        return _updateStatus and _installStatus and _upgradeStatus

    def _printSubDirectiveError(self, sdName):
        self._log.error("Error executing %s subdirective" % sdName)

    def _setupMacOS(self):
        self._platformName = "mac"
        self._setupBrew()

    def _setupLinux(self):
        self._platformName = "linux"

        # check the package manager that is installed and use that
        # the following are the supported package managers for now
        # name, dict lookup, file, setup function
        managers = [
            ("apt-get", "apt", "/etc/debian_version", "_setupAptGet"),
            ("pacman", "pac", "/etc/arch-release", "_setupPacman"),
            ("dnf", "dnf", "/etc/redhat-release", "_setupDnf")
        ]
        self._selectPackageManager(managers)

    def _selectPackageManager(self, packageManagers):
        for name, lookup, file, func in packageManagers:
            if os.path.exists(file):
                # set the package manager name and run the setup function
                self._packageManagerName = name
                self._dictLookup = lookup
                eval("self." + func + "()")
                break

    def _setupBrew(self):
        self._packageManagerName = "brew"
        self._dictLookup = self._packageManagerName

        # add a brew installation if not already installed
        self._installCommand = "brew install"
        self._existsCheck = "brew ls"
        self._upgradeCommand = "brew upgrade"

    def _setupAptGet(self):
        self._installCommand = "sudo apt-get install -y"
        self._existsCheck = "apt-cache show"
        self._updateCommand = "sudo apt-get update"
        self._upgradeCommand = "sudo apt-get dist-upgrade -y"

    def _setupPacman(self):
        baseCommand = "sudo pacman --noconfirm %s"
        self._installCommand = baseCommand % "-S"
        self._existsCheck = "pacman -Si"
        self._updateCommand = baseCommand % "-Syy"
        self._upgradeCommand = baseCommand % "-Syu"

    def _setupDnf(self):
        self._installCommand = "sudo dnf install -y"
        self._existsCheck = "dnf list"
        self._updateCommand = "sudo dnf check-update"
        self._upgradeCommand = "sudo dnf upgrade -y"

    def _doInstall(self, pkgList):
        if self._installCommand != "":
            # append the package to the install command and run the command
            success = True
            for pkg in pkgList:
                if isinstance(pkg, str):
                    self._log.info("Installing package: %s" % pkg)
                    exists = self._pkgExists(pkg)
                    existsInDict = True
                elif isinstance(pkg, list):
                    self._log.info("Selecting package from {}".format(pkg))
                    exists, pkg = self._getPkgNameFromList(pkg)
                    existsInDict = True
                    if exists:
                        self._log.info("Found package: %s - Installing" % pkg)
                elif isinstance(pkg, dict):
                    self._log.info("Selecting optional package from {}".format(pkg))
                    existsInDict, exists, pkg, directive = self._getPkgNameFromDict(pkg)
                    if exists:
                        self._log.info("Found package: %s for %s - Installing" % (pkg, directive))
                else:
                    # invalid data
                    # this should be handled above the plugin level
                    raise ValueError("Invalid data given to omnipkg-install")

                # first check that item exists in data (only relevant for dictionary data)
                if not existsInDict:
                    self._log.lowinfo("Skipping installation as no package specified for %s or %s" % (self._packageManagerName, self._platformName))
                    # otherwise skip if package doesn't exist
                elif not exists:
                    self._log.lowinfo("Skipping installation as package does not exist")
                else:
                    cmd = "%s %s" % (self._installCommand, pkg)
                    result = self._bootstrap(cmd)
                    if not result:
                        success = False  # if one fails we still continue
                        self._log.warning("Package %s failed to install" % pkg)

            return success
        else:
            # there should always be an install command
            return False

    def _doUpdate(self):
        if self._updateCommand != "":
            self._log.info("Begin Update <%s>" % self._updateCommand)
            return self._bootstrap(self._updateCommand)
        else:
            # there doesn't have to be an update command
            return True

    def _doUpgrade(self):
        if self._upgradeCommand != "":
            self._log.info("Begin Upgrade <%s>" % self._upgradeCommand)
            return self._bootstrap(self._upgradeCommand, silent=False)
        else:
            # there doesn't have to be an upgrade command
            return True

    def _pkgExists(self, pkg):
        if self._existsCheck != "":
            cmd = "%s %s" % (self._existsCheck, pkg)
            result = self._bootstrap(cmd)
            return result
        else:
            # assume the package exists if no check
            return True

    def _getPkgNameFromList(self, pkgList):
        for pkg in pkgList:
            if self._pkgExists(pkg):
                return (True, pkg)

        return (False, "")

    def _getPkgNameFromDict(self, pkgDict):
        # first check that there is an item for the current package manager
        # otherwise check for a platform directive (linux or mac)
        # otherwise check for an else directive
        # otherwise we don't install for this package
        if self._dictLookup in pkgDict:
            pkg = pkgDict[self._dictLookup]
            return (True, self._pkgExists(pkg), pkg, self._dictLookup)
        elif self._platformName in pkgDict:
            pkg = pkgDict[self._platformName]
            return (True, self._pkgExists(pkg), pkg, self._platformName)
        elif self._dictLookupElse in pkgDict:
            pkg = pkgDict[self._dictLookupElse]
            return (True, self._pkgExists(pkg), pkg, self._dictLookupElse)
        else:
            return (False, False, None, None)

    def _bootstrap(self, cmd, silent=True):
        with open(os.devnull, 'w') as devnull:
            if silent:
                stdout = stderr = devnull
            else:
                stdout = stderr = None

            result = subprocess.call(
                cmd,
                shell=True,
                stdout=stdout,
                stderr=stderr,
                cwd=self._context.base_directory())
            return result == 0
        return True

    def _bootstrapBrew(self):
        # install brew
        link = "https://raw.githubusercontent.com/Homebrew/install/master/install.sh"
        cmd = """hash brew || /bin/bash -c "$(curl -fsSL {0})";
              brew update""".format(link)
        self._bootstrap(cmd)
