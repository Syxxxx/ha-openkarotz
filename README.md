# Intégration OpenKarotz pour Home Assistant

Intégration complète pour le lapin OpenKarotz (firmware FreeRabbit) dans Home Assistant.

Cette intégration utilise une **architecture hybride** pour une performance et une fiabilité maximales :
1.  **Polling (Sondage) :** Un `DataUpdateCoordinator` interroge l'API `/cgi-bin/status` du Karotz pour obtenir un état en temps réel (non-optimiste) de la LED, du mode veille et du volume.
2.  **Push (Poussée) :** Un Webhook sécurisé reçoit instantanément les événements des **Tags RFID** et des **Boutons**, s'intégrant parfaitement aux systèmes natifs de Home Assistant.

---

## ✨ Fonctionnalités

* **Configuration via l'Interface Utilisateur** (UI).
* **Entités d'État (Non-Optimistes)** :
    * `light.karotz_led` : Représente l'état et la couleur réels de la LED, avec support du clignotement simple (`flash`).
    * `switch.karotz_veille` : Interrupteur pour voir et contrôler l'état de veille.
    * `media_player.karotz_lecteur` : Affiche le niveau de volume réel.
* **Entités d'Action** :
    * `select.karotz_effet_led` : Un sélecteur (dropdown) pour contrôler la vitesse de clignotement (rapide, normal, lent, aucun).
    * `media_player.karotz_lecteur` : S'intègre avec `tts.say`, `play_media` (URL) et le contrôle de volume (Set, Up, Down).
    * `camera.karotz_camera` : Permet de prendre des snapshots (nécessite un correctif sur le Karotz, voir ci-dessous).
    * `cover.karotz_oreilles` : Représente les oreilles (0% = bas, 100% = haut).
* **Intégration RFID Native** :
    * Déclenche l'événement `tag_scanned` natif de Home Assistant.
* **Triggers d'Appareil (Boutons)** :
    * Permet d'utiliser les clics de bouton (Simple, Double, Triple, Long) comme déclencheurs dans l'éditeur d'automatisations.
* **Capteurs de Diagnostic** :
    * `sensor.karotz_webhook_url` : (Désactivé par défaut) Affiche l'URL à utiliser pour le script `dbus_watcher`.
    * ...et de nombreux autres capteurs (désactivés par défaut) : Espace disque, % disque utilisé, Version Firmware, Adresse MAC, Nombre de tags, etc.

---

## ⚙️ Installation (Recommandée : HACS)

1.  Assurez-vous d'avoir HACS (Home Assistant Community Store) installé.
2.  Allez dans **HACS > Intégrations**.
3.  Cliquez sur les trois points en haut à droite et choisissez **Dépôts personnalisés**.
4.  Dans le champ "Dépôt", collez l'URL de ce dépôt GitHub (`https://github.com/Syxxxx/ha-openkarotz`).
5.  Dans le champ "Catégorie", choisissez **Intégration**.
6.  Cliquez sur **Ajouter**.
7.  Vous devriez maintenant voir "OpenKarotz" dans la liste. Cliquez sur **Installer**.
8.  Redémarrez Home Assistant.

---

## 🚀 Configuration

La configuration se fait en **deux étapes obligatoires** et une étape optionnelle pour la caméra.

### Étape 1 : Ajouter l'intégration dans Home Assistant

1.  Allez dans **Paramètres > Appareils et services**.
2.  Cliquez sur **Ajouter une intégration** (bouton bleu en bas à droite).
3.  Recherchez **"OpenKarotz"** et cliquez dessus.
4.  Entrez l'**adresse IP** de votre Karotz et donnez-lui un nom.
5.  Cliquez sur **Valider**.

### Étape 2 : Configurer le Webhook "Push" (RFID/Boutons)

Pour que les RFID et les boutons fonctionnent, vous devez modifier un script sur votre Karotz.

1.  **Trouver votre URL de Webhook :**
    * Allez dans **Paramètres > Appareils et services** et cliquez sur **Entités**.
    * Filtrez par votre appareil Karotz (ex: "Karotz Salon").
    * Vous verrez une entité `sensor.karotz_salon_webhook_url` qui est **désactivée**.
    * Cliquez dessus, puis cliquez sur l'icône "engrenage" en haut à droite et **activez l'entité**.
    * Retournez à l'état de l'entité (vous devrez peut-être recharger la page) et **copiez l'URL complète**. Elle ressemblera à `http://[VOTRE_IP_HA]:8123/api/webhook/[LONG_ID_ALEATOIRE]`.

2.  **Modifier le script `dbus_watcher` sur le Karotz :**
    * Connectez-vous en SSH à votre Karotz. **Le nom d'utilisateur est `karotz`** :
    ```bash
    ssh karotz@ADRESSE_IP_DU_KAROTZ
    ```
    * Ouvrez le script en édition : `vi /usr/scripts/dbus_watcher`
    * **Tout en haut** du script (juste après `#!/bin/bash`), ajoutez vos variables et une nouvelle fonction `send_to_ha` :

    ```bash
    #!/bin/bash
    
    # === DEBUT CONFIGURATION HOME ASSISTANT ===
    # Mettez ici l'URL complète copiée depuis le capteur sensor.karotz_webhook_url
    HA_WEBHOOK_URL="http://[VOTRE_IP_HA]:8123/api/webhook/[LONG_ID_ALEATOIRE]"
    
    # Fonction pour envoyer du JSON à Home Assistant en arrière-plan
    send_to_ha() {
        local data=$1
        # Log local pour le débogage
        Log "[HA Send]" "${data}"
        
        # Utilise curl en POST, envoie du JSON, avec un timeout court,
        # et en arrière-plan (&) pour ne pas bloquer le script.
        curl -X POST \
             -H "Content-Type: application/json" \
             -d "${data}" \
             "${HA_WEBHOOK_URL}" \
             -o /tmp/ha_curlout -s --connect-timeout 2 &
    }
    # === FIN CONFIGURATION HOME ASSISTANT ===
    
    # (...la suite de votre script... source /usr/www/cgi-bin/setup.inc etc...)
    ```

    * **Modifier la gestion des boutons :**
        * Trouvez les sections `click`, `dclick`, `tclick`, `lclick_start`.
        * **Juste après** la ligne `if [ $? -eq 0 ]; then`, ajoutez l'appel à la fonction `send_to_ha`.

    *Exemple pour `click` :*
    ```bash
     echo $line | grep "member=click"
     if [ $? -eq 0 ]; then
         send_to_ha "{\"event_type\": \"button\", \"event\": \"click\"}"
         PlaySound $CNF_DATADIR/Sounds/${SOUND}
     fi
    ```
    *Faites de même pour `dclick`, `tclick`, `lclick_start`, `lclick_stop`.*

    * **Modifier la gestion RFID :**
        * Trouvez la section `RFID HANDLER`.
        * Localisez l'endroit où le tag est détecté et validé (là où se trouvaient vos anciens `curl` vers Jeedom).
        * Remplacez les anciens `curl` par **un seul appel** à `send_to_ha` avec l'ID du RFID.

    *Exemple pour `RFID` (à placer dans la section `else` de `if [ -e "$CNF_DATADIR/Run/rfid.record" ]; then`...) :*
    ```bash
              # ... (logique existante)
              if [ -e "$CNF_DATADIR/Rfid/${RFID_ID}.rfid" ]; then
                  Leds FF0000 000000 0 1
                  Log "[Rfid]" "Calling Home Assistant Webhook for RFID: ${RFID_ID}"
                  LedsRestore

                  # === ENVOI VERS HOME ASSISTANT ===
                  send_to_ha "{\"event_type\": \"rfid\", \"rfid_id\": \"${RFID_ID}\"}"
                  
                  # Supprimez/commentez les anciens curl vers Jeedom
                  # curl -g --connect-timeout 30 ... (ancienne ligne)
                  # curl -g --connect-timeout 30 ... (ancienne ligne)
              else
              # ... (le reste de la logique d'erreur)
    ```

3.  **Sauvegardez le fichier** (sur `vi`, tapez `:wq`).
4.  Redémarrez votre Karotz ou relancez le script `dbus_watcher`.

### Étape 3 (Optionnel mais Recommandé) : Corriger le bug de la Caméra

Sur certaines versions d'OpenKarotz, le script de la caméra est "cassé" et envoie des en-têtes HTTP non valides, ce qui empêche Home Assistant d'afficher l'image.

1.  Connectez-vous en SSH à votre Karotz : `ssh karotz@ADRESSE_IP_DU_KAROTZ`
2.  Ouvrez le script de la caméra en édition :
    ```bash
    vi /usr/www/cgi-bin/snapshot_view
    ```
3.  Localisez la ligne qui dit simplement :
    ```bash
    TakeSnapshot
    ```
4.  Modifiez cette ligne pour rediriger la sortie de cette fonction vers `/dev/null`. Elle doit devenir :
    ```bash
    TakeSnapshot > /dev/null 2>&1
    ```
5.  Sauvegardez le fichier (`:wq`). Il n'y a pas besoin de redémarrer. L'entité caméra dans Home Assistant devrait commencer à fonctionner.

---

## 💡 Utilisation et Services

### Entités principales

* **`switch.karotz_veille`** : Mettez-le sur `ON` pour endormir le lapin, `OFF` pour le réveiller.
* **`media_player.karotz_lecteur`** :
    * Utilisez le service `tts.say` pour le faire parler.
    * Utilisez le service `media_player.play_media` avec une URL pour streamer un son.
    * Contrôlez le volume directement depuis l'interface.
* **`cover.karotz_oreilles`** : Réglez la position de 0% (bas) à 100% (haut).
* **`light.karotz_led`** : Choisissez une couleur.
* **`select.karotz_effet_led`** : **Nouveau !** C'est le contrôle principal pour le clignotement.

#### 💡 Contrôler la Vitesse de Clignotement (Effets)

Pour contrôler le clignotement, vous n'avez plus besoin de créer de "helper" manuel. L'intégration fournit maintenant une entité `select.karotz_effet_led`.

1.  Ajoutez l'entité `light.karotz_led` à votre tableau de bord (pour la couleur).
2.  Ajoutez l'entité `select.karotz_effet_led` à votre tableau de bord.
3.  Utilisez le sélecteur (dropdown) pour choisir la vitesse :
    * `none` (Clignotement désactivé)
    * `pulse_fast` (Rapide)
    * `pulse_normal` (Normal)
    * `pulse_slow` (Lent)

Le changement de ce sélecteur allumera automatiquement la LED (en vert par défaut, ou sa couleur actuelle si elle est déjà allumée) avec la vitesse de clignotement choisie.

### Services Personnalisés

Cette intégration ajoute des services spécifiques pour contrôler les sons locaux du Karotz.

#### `openkarotz.play_sound`
Joue un son local par son nom de fichier (ID).
```yaml
# Exemple d'automatisation
action:
  - service: openkarotz.play_sound
    target:
      entity_id: media_player.karotz_lecteur
    data:
      sound_id: "new_mail.mp3" # ID du son sur le Karotz
```

#### `openkarotz.play_mood`
Joue une "humeur" (animation son + lumière) par son numéro.
```yaml
action:
  - service: openkarotz.play_mood
    target:
      entity_id: media_player.karotz_lecteur
    data:
      mood_id: 10 # Numéro de l'humeur
```

#### `openkarotz.play_radio`
Joue une radio pré-configurée sur le Karotz par son numéro.
```yaml
action:
  - service: openkarotz.play_radio
    target:
      entity_id: media_player.karotz_lecteur
    data:
      radio_id: 1 # Numéro de la radio
```

### Automatisations (RFID et Boutons)

#### 1. Déclencher une action sur un scan RFID

Créez une automatisation avec le déclencheur `tag_scanned`.

```yaml
alias: "RFID Karotz - Jouer la radio"
description: "Joue France Info quand le tag 0123ABC est scanné sur le Karotz"
trigger:
  - platform: tag
    tag_id: "0123ABC" # Remplacez par l'ID de votre tag
condition:
  # Filtrer pour être sûr que c'est le Karotz qui a scanné (facultatif mais propre)
  - condition: template
    value_template: "{{ trigger.device_id == 'ID_DE_VOTRE_APPAREIL_KAROTZ' }}"
action:
  - service: media_player.play_media
    target:
      entity_id: media_player.votre_media_player
    data:
      media_content_id: "[http://ice.radiofrance.fr/franceinfo-hifi.aac](http://ice.radiofrance.fr/franceinfo-hifi.aac)"
      media_content_type: "audio/aac"
mode: single
```

#### 2. Déclencher une action sur un clic de bouton

Créez une automatisation avec un déclencheur d'Appareil.

1.  Allez dans **Paramètres > Automatisations**.
2.  Créez une nouvelle automatisation.
3.  Dans **Déclencheur**, choisissez **Appareil**.
4.  Dans **Appareil**, choisissez votre **Karotz**.
5.  Dans **Déclencheur**, vous verrez la liste :
    * `Bouton : Clic simple`
    * `Bouton : Double clic`
    * `Bouton : Clic long (début)`
    * etc.
6.  Ajoutez vos actions (ex: `light.toggle` pour allumer/éteindre une lumière).