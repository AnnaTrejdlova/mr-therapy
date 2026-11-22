# Dokumentace nasazení systému 

Tento dokument obsahuje stručný návod k nasazení kompletní infrastruktury systému, která se skládá ze serverové části (backend, frontend, databáze) a klientské MR aplikace pro Meta Quest 3.

## Předpoklady 
Před začátkem nasazení se ujistěte, že máte k dispozici:
* Nainstalovaný **Docker**.
* Vývojové prostředí **Unity** (s modulem Android Build Support).
* Headset **Meta Quest 3** připojený k počítači.
* **MQTT broker**. Projekt obsahuje lokální broker Mosquitto, který se spouští spolu s ostatními kontejnery (viz [Část 0](#část-0-lokální-mqtt-broker-mosquitto)). Případně lze použít externí broker s přihlášením jménem a heslem (TLS na portu 8883).
* **Společná lokální síť:** Pro správné fungování video streamu (WebRTC) musí být headset i počítač s asistenční aplikací připojeny do **stejné lokální sítě (stejná Wi-Fi)**.

---

## Část 0: Lokální MQTT broker (Mosquitto)

Broker běží jako služba `mqtt_broker` v `docker-compose.yaml` a vyžaduje přihlášení jménem a heslem. Konfigurace je v `mosquitto/config/mosquitto.conf`.

Všechny příkazy spouštějte v **PowerShellu** ze složky `External_Station_headset_app`. Místo `mrtherapy` a `VASE_HESLO` použijte vlastní jméno a heslo.

**1. Jméno a heslo v `.env`**
Přihlašovací údaje se zadávají jen do souboru `backend/.env` (viz Část 1), stejného, který používá backend:
```
MQTT_USERNAME=mrtherapy
MQTT_PASSWORD=VASE_HESLO
```
Broker si při každém spuštění z těchto hodnot sám vytvoří uživatele. Soubor s hesly se generuje uvnitř kontejneru, takže ho není potřeba vytvářet ručně ani commitovat. Pokud některá z hodnot chybí, broker se nespustí a v logu napíše, která.

**2. Spuštění brokeru**
```powershell
docker compose up -d
```
Kontrola logu: `docker compose logs mqtt_broker`. Má obsahovat řádek `MQTT user 'mrtherapy' set from backend/.env` a na konci `mosquitto version ... running`.

**3. Změna hesla**
Upravte `MQTT_PASSWORD` v `backend/.env` a znovu spusťte `docker compose up -d`. Docker pozná změnu `.env` a broker i backend vytvoří znovu s novým heslem. Příkaz `docker compose restart` **nestačí**, protože `.env` znovu nenačte. Nové heslo je potom nutné zadat i do Unity assetu (krok 6) a aplikaci znovu buildnout do headsetu.

**4. Port**
Broker je z počítače a z lokální sítě dostupný na portu **11883**, ne na výchozím 1883. Windows (Hyper-V) si často rezervuje rozsah portů 1835–1934, takže 1883 nelze otevřít. Backend běží v Dockeru a připojuje se uvnitř Dockeru na `mqtt_broker:1883`. Vyhrazené porty zobrazíte příkazem `netsh interface ipv4 show excludedportrange protocol=tcp`.

**5. Povolení ve firewallu**
Aby se headset k brokeru připojil, povolte port 11883 ve Windows Firewallu (PowerShell **jako správce**, jednorázově):
```powershell
New-NetFirewallRule -DisplayName "MQTT broker (mr-therapy)" -Direction Inbound -Protocol TCP -LocalPort 11883 -Action Allow -Profile Private
```
Síť, ke které je počítač připojen, musí být v systému Windows nastavená jako **soukromá** (Private).

**6. Kam údaje vyplnit**

| Kde | Adresa | Port | TLS | Jméno / heslo |
|---|---|---|---|---|
| `backend/.env` (Část 1) | `MQTT_BROKER_ADDRESS=mqtt_broker` | `MQTT_BROKER_PORT=1883` | `MQTT_USE_TLS=False` | `MQTT_USERNAME` / `MQTT_PASSWORD` |
| Unity asset (Část 2) | IP adresa počítače v lokální síti, např. `192.168.0.126` | `11883` | `UseTls` vypnuto | `Username` / `Password` |

IP adresu počítače zjistíte příkazem `ipconfig` (řádek *IPv4 Address* u Wi-Fi nebo Ethernetu, ne u adaptérů `vEthernet`). Pro Unity nepoužívejte `localhost` ani `mqtt_broker`, headset tyto adresy nezná. Pokud se IP adresa počítače mění, nastavte si v routeru pro počítač pevnou adresu (DHCP rezervace).

**7. Ověření přihlášení**
Následující příkaz se přihlásí přes IP adresu počítače, tedy stejně jako headset, a vypisuje zprávy z aplikace (např. heartbeat každých 10 s). Ukončíte ho Ctrl+C.
```powershell
docker run --rm eclipse-mosquitto:2 mosquitto_sub -h 192.168.0.126 -p 11883 -u mrtherapy -P VASE_HESLO -t "/unitymap/#" -v
```
Chyba `Connection Refused: not authorised` znamená špatné jméno nebo heslo, případně broker po změně `.env` nebyl znovu vytvořen příkazem `docker compose up -d` (krok 3).

---

## Část 1: Nasazení serverové části (Docker)

Serverová architektura je plně kontejnerizována, instalaci závislostí a prostředí řeší automaticky Docker.

**1. Konfigurace prostředí (.env)**
Ve složce s projektem vytvořte soubor `.env` na základě přiložené předlohy `.env-template` a doplňte do něj vaše vlastní přístupové údaje k databázi a MQTT brokeru. Pro lokální broker použijte hodnoty z tabulky v [Části 0](#část-0-lokální-mqtt-broker-mosquitto), krok 6.

**2. Spuštění kontejnerů**
Otevřete příkazovou řádku ve složce projektu a spusťte příkaz:
```bash
docker-compose up -d --build
```
*Tento příkaz automaticky sestaví a spustí backend, frontend i databázi. Backend logicky vyčká na inicializaci databázového stroje.*

---

## Část 2: Nasazení klientské aplikace (Unity)

Klientská aplikace je nasazována přímo z vývojového prostředí.

**1. Nastavení MQTT v Unity**
Otevřete projekt klientské aplikace v prostředí Unity. Přejděte do složky `data/` v modulu MQTT, kde se nachází šablonový soubor s konfigurací. Tento soubor v Unity zduplikujte (Ctrl+D) nebo zkopírujte, odstraňte z jeho názvu `_example` (nebo ho pojmenujte např. `MQTTLocalCredentials`, git ignoruje všechny soubory `MQTT*Credentials.asset`) a v Inspectoru vyplňte vaše vlastní připojovací parametry (IP brokera, port, login a heslo). Pro lokální broker viz [Část 0](#část-0-lokální-mqtt-broker-mosquitto), krok 6. Pokud prefab `_MQTT_System` hlásí `MQTT Credentials not assigned!`, přetáhněte nový asset do pole `Credentials` u komponent Publisher a Subscriber.
**Důležité:** Nezasahujte do prefixů, prefix `unitymap` musí zůstat zachován pro správné směrování zpráv!

**2. Build do zařízení**
Ujistěte se, že máte headset Meta Quest 3 připojený k PC a v Unity je zvolena cílová platforma Android. Následně v menu zvolte `File -> Build and Run`. Aplikace se zkompiluje a automaticky spustí v brýlích.

---

## Část 3: Fyzická kostka pro hru Cube Arc

Hra *Přenášení kostky po oblouku* sleduje skutečnou kostku kamerou brýlí. Na každé stěně kostky musí být nalepený jeden AprilTag marker (rodina `tagStandard41h12`, ID 0–5).

**1. Tisk markerů**
Hotový arch pro kostku o hraně 50 mm je v `Documentation/markers/cube_markers_50mm.pdf` (tag má 45 mm). Tiskněte ve **100 %** (vypněte „Přizpůsobit stránce“) a pravítkem zkontrolujte, že měřítko 100 mm na archu opravdu měří 100 mm. Tiskněte matně, lesklý papír odráží světlo a detekce pak selhává.

Menší markery jsou kamerou vidět jen na kratší vzdálenost. Pokud detekce na 50 mm kostce vypadává, zkuste u `AprilTagCubeTracker` nastavit `Quad Decimation` na 1 (přesnější, ale pomalejší), nebo použijte větší kostku. Pro jinou velikost kostky (40–85 mm) vygenerujte nový arch:
```bash
python Documentation/markers/generate_cube_markers.py --edge-mm 60
```
Skript vypíše hodnoty `cubeEdge` a `tagSize`, které je pak potřeba zadat v Unity u komponenty `AprilTagCubeTracker` v prefabu hry `CubeArcGame`.

**2. Lepení**
Vystřihněte šest čtverců podle šedých čar a nalepte je tak, jak je napsáno pod každým z nich. Šipka nad tagem označuje jeho horní hranu. Postavte kostku stěnou s ID 0 nahoru a dívejte se na stěnu s ID 2:

| ID | Stěna | Horní hrana tagu |
|---|---|---|
| 0 | horní | směrem ke stěně ID 3 (od vás) |
| 1 | spodní | směrem ke stěně ID 3 |
| 2 | přední (k vám) | nahoru |
| 3 | zadní | nahoru |
| 4 | levá | nahoru |
| 5 | pravá | nahoru |

Markery musí ležet rovně, bez bublin a bez přelepení průhlednou páskou s odlesky.

**3. Ověření sledování**
V prefabu `CubeArcGame` zapněte u `MainCubeArcManager` volbu `Show Tracking Debug`. Na brýlích se pak u kostky zobrazí osy každého rozpoznaného tagu (modrá osa Z musí mířit dovnitř kostky), žlutý obrys odhadnuté kostky a frekvence detekce. Obrys má sedět na skutečné kostce i při otáčení. Detekce by měla běžet alespoň 15× za sekundu. Podrobné hodnoty se vypisují i do logu (`adb logcat -s Unity`, řádky `[CubeTracker]`).

Bez vytištěné kostky lze hru vyzkoušet s volbou `Force Controller Source`: kostku pak zastupuje pravý ovladač (v Editoru se ovladač používá vždy).
