# dotbot-omnipkg

Plugin for [dotbot](https://github.com/anishathalye/dotbot) to streamline package management,
installs packages with the system package manager on Linux or brew if on OSX.  
Currently supports:
* ```apt-get```
* ```pacman```
* ```brew```

## Installation
Just add it as a submodule of your dotfiles repository
```bash
git submodule add https://github.com/code-maniac/dotbot-omnipkg
```  
Modify ```install``` script so that it automatically enables ```dotbot-omnipkg``` plugin
```bash
BASEDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OMNIPKGPLUGIN="${BASEDIR}/dotbot-omnipkg/omnipkg.py"

"${BASEDIR}/${DOTBOT_DIR}/${DOTBOT_BIN}" \
    -d "${BASEDIR}" \
    -c "${CONFIG}" \
    -p "${OMNIPKGPLUGIN}" \
    "${@}" 
```

## Usage
The following directives are supported:
* ```omnipkg-update```
* ```omnipkg-install```
* ```omnipkg-upgrade```

Update package lists for the installed package manager:
```yaml
- omnipkg-update: true
```
  
Update currently installed packages:
```yaml
- omnipkg-upgrade: true
```
  
Install the packages in the list
```yaml
- omnipkg-install: [
    kitty,
    tmux,
    zsh,
    neovim
  ]
```
Install single package from the list:
```yaml
- omnipkg-install: [
    [ python3, python ]
  ]
```
Priority is given to first package in the list.  
To be used when a package has a different name depending on the distro that it's being installed on.
In the above example ```python3``` is named ```python3``` on OSX and Ubuntu but is named ```python``` on Arch.

# Roadmap
1. Add unit testing for existing features
2. Add directive to support adding new PPA repositories
3. Add support for additional package managers - ```yum```, ```zypp```, ```emerge``` etc

# License
[MIT](https://choosealicense.com/licenses/mit/)
