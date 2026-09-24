#!/bin/bash
# add-uchni.sh uchni.csv   (логін,пароль,клас,Прізвище,Ім'я) — резервний шлях без застосунку
while IFS=, read -r login pass klas prizv imya; do
  [ -z "$login" ] && continue
  samba-tool user create "$login" "$pass" \
    --given-name="$imya" --surname="$prizv" \
    --description="$klas" --userou='OU=Uchni' \
  && samba-tool group addmembers "uchni-$klas" "$login" \
  && echo "OK $login"
done < "$1"
