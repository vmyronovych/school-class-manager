#!/bin/bash
# add-uchni.sh uchni.csv   (логін,пароль,клас,Прізвище,Ім'я; логін — прізвище.ім'я.рік_народження, клас — 2025-4a)
# Резервний шлях без застосунку.
# Обов'язковий профіль (docs/deployment.md, Етап 9, п. 9) — лише коли він уже існує.
opt=()
[ -d /var/lib/samba/sysvol/ad.school.lan/scripts/profiles/uchni.V6 ] \
  && opt=(--profile-path='\\dc1\netlogon\profiles\uchni')
while IFS=, read -r login pass klas prizv imya; do
  [ -z "$login" ] && continue
  samba-tool user create "$login" "$pass" \
    --given-name="$imya" --surname="$prizv" \
    --userou='OU=Uchni' "${opt[@]}" \
  && samba-tool group addmembers "uchni-$klas" "$login" \
  && echo "OK $login"
done < "$1"
