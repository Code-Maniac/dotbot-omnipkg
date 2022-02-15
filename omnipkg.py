import dotbot
import os
import sys
import subprocess


class OmniPkg(dotbot.Plugin):
    # The supported directives
    _installDirective = "omnipkg-install"
    _updateDirective = "omnipkg-update"
    _upgradeDirective = "omnipkg-upgrade"

    # The name of the package manager that has been found
    _packageManagerName = ""

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
        return directive in (
            self._installDirective,
            self._updateDirective,
            self._upgradeDirective)

    def handle(self, directive, data):
        # select the directive to run
        if directive == self._installDirective:
            return self._doInstall(data)
        elif directive == self._updateDirective:
            return self._doUpdate()
        elif directive == self._upgradeDirective:
            return self._doUpgrade()
        else:
            raise ValueError('OmniPkg cannot handle directive %s' % directive)

    def _setupMacOS(self):
        self._setupBrew()

    def _setupLinux(self):
        # check the package manager that is installed and use that
        # the following are the supported package managers for now
        managers = [
            ("apt-get", "/etc/debian_version", "_setupAptGet"),
            ("pacman", "/etc/arch-release", "_setupPacman")
        ]
        self._selectPackageManager(managers)

    def _selectPackageManager(self, packageManagers):
        for name, file, func in packageManagers:
            if os.path.exists(file):
                # set the package manager name and run the setup function
                self._packageManagerName = name
                eval("self." + func + "()")
                break

    def _setupBrew(self):
        # add a brew installation if not already installed
        self._installCommand = "brew install"
        self._existsCheck = "brew ls"
        self._upgradeCommand = "brew upgrade"

    def _setupAptGet(self):
        self._installCommand = "sudo apt-get install -y %s"
        self._updateCommand = "sudo apt-get update"
        self._upgradeCommand = "sudo apt-get dist-upgrade -y"

    def _setupPacman(self):
        baseCommand = "sudo pacman --noconfirm %s"
        self._installCommand = baseCommand % "-S"
        self._updateCommand = baseCommand % "-Syy"
        # no difference here between upgrade and dist-upgrade
        self._upgradeCommand = baseCommand % "-Syu"

    def _doInstall(self, pkgList):
        if self._installCommand != "":
            # append the package to the install command and run the command
            success = True
            for pkg in pkgList:
                self._log.info("Installing package: %s" % pkg)
                if not self._pkgExists(pkg):
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
