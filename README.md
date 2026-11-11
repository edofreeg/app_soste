# Soste Autisti

App Android (Kivy) per registrare soste: autista, luogo, arrivo, partenza, intervallo.
Export CSV con separatore `;` (colonne: autista;luogo;data_ora_arrivo;data_ora_partenza;intervallo_sosta).

## Pubblicare l'APK su GitHub
1. Crea un repository e carica questi file.
2. `git tag v0.1.0 && git push origin v0.1.0`
3. GitHub Actions compila (15-30 min la prima volta) e allega l'APK alla Release.
4. Dal telefono apri la Release, scarica l'APK e installalo (consenti "origini sconosciute").

Richiede Android 10 o superiore. Per cambiare l'identificativo modifica `package.domain` in `buildozer.spec`.
