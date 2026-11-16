#!/bin/bash
# BV-250 / CTO-61 §2.0: the test account, its folders, the prompt and the host
# name. Plan B when sysadminctl cannot create the account: the runner account
# with HOME pointing at a temporary «prueba» folder. Writes LAB_USER, LAB_HOME
# and LAB_ACCOUNT to $GITHUB_ENV; nothing here touches a key.
set -euo pipefail

account=prueba
if sudo sysadminctl -addUser prueba -fullName prueba -home /Users/prueba >/dev/null 2>&1 &&
  id prueba >/dev/null 2>&1; then
  sudo mkdir -p /Users/prueba
  sudo chown prueba:staff /Users/prueba
  user=prueba home=/Users/prueba
else
  echo "::warning::sysadminctl could not create the account prueba: plan B (runner with HOME=\$RUNNER_TEMP/prueba)"
  account=runner_home
  user=$(id -un) home="$RUNNER_TEMP/prueba"
  mkdir -p "$home"
fi

as_user() { if [ "$user" = "$(id -un)" ]; then "$@"; else sudo -u "$user" -H "$@"; fi; }

as_user mkdir -p "$home/Desktop" "$home/Documents" "$home/Downloads" "$home/proyecto"
as_user /bin/sh -c "printf '# proyecto\n\nProyecto de prueba del laboratorio de RosmarOps.\n' > '$home/proyecto/README.md'"
as_user /bin/sh -c "printf '{\n  \"name\": \"proyecto\",\n  \"version\": \"1.0.0\",\n  \"private\": true\n}\n' > '$home/proyecto/package.json'"
# Nothing else in the home folder: no keys, real or fake.
[ "$account" = runner_home ] || sudo find "$home" -mindepth 1 -maxdepth 1 -name '.*' -exec rm -rf {} +

# §2.0.2: the host name «lab», so no runner name appears.
sudo scutil --set HostName lab
sudo scutil --set LocalHostName lab
sudo scutil --set ComputerName lab

{
  echo "LAB_USER=$user"
  echo "LAB_HOME=$home"
  echo "LAB_ACCOUNT=$account"
} >> "$GITHUB_ENV"
echo "account: $account ($user, $home)"
