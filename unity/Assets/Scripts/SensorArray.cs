using UnityEngine;

// M07: háromszenzoros (bal-közép-jobb) elrendezés, kapcsolható
// egy-/háromszenzoros mód között. Ezt a scriptet Claude írta
// (nem Codex), lásd AI_USAGE.md.
//
// Működés:
// - A RoverChassis-ra kerül, három ColorSensor komponensre
//   hivatkozik (bal, közép, jobb).
// - haromSzenzorosMod == false: csak a közép szenzor GameObject-je
//   aktív, a bal/jobb ki van kapcsolva (SetActive(false)) - ez az
//   "egyszenzoros" mód.
// - haromSzenzorosMod == true: mind a három szenzor aktív.
// - A mód futásidőben (Play módban) is átkapcsolható a
//   HaromSzenzorosModBeallitasa metódussal, vagy Inspectorban
//   a checkbox módosításával (OnValidate frissíti azonnal).
// - Az aggregált kimenet (BalErtek/KozepErtek/JobbErtek,
//   BalFeher/KozepFeher/JobbFeher) mindig elérhető, de a
//   kikapcsolt szenzorok GameObject-je nem fut (nincs
//   raycast/zaj-számítás), így a zaj-seed determinizmusa a
//   bekapcsolt szenzorokra nézve nem sérül.
public class SensorArray : MonoBehaviour
{
    [Header("Szenzor-hivatkozások")]
    [SerializeField]
    private ColorSensor balSzenzor;
    [SerializeField]
    private ColorSensor kozepSzenzor;
    [SerializeField]
    private ColorSensor jobbSzenzor;

    [Header("Mód")]
    [Tooltip("Ha be van jelölve: mind a három szenzor aktív. " +
             "Ha nincs: csak a középső szenzor aktív (egyszenzoros mód).")]
    [SerializeField]
    private bool haromSzenzorosMod = false;

    public bool HaromSzenzorosMod => haromSzenzorosMod;

    // --- Nyilvános, csak olvasható kimenetek (aggregátum) ---
    public float BalErtek => balSzenzor != null ? balSzenzor.MertIntenzitas : 0f;
    public float KozepErtek => kozepSzenzor != null ? kozepSzenzor.MertIntenzitas : 0f;
    public float JobbErtek => jobbSzenzor != null ? jobbSzenzor.MertIntenzitas : 0f;

    public bool BalFeher => balSzenzor != null && haromSzenzorosMod && balSzenzor.FeherVonalon;
    public bool KozepFeher => kozepSzenzor != null && kozepSzenzor.FeherVonalon;
    public bool JobbFeher => jobbSzenzor != null && haromSzenzorosMod && jobbSzenzor.FeherVonalon;

    private void Awake()
    {
        FrissitsAktivAllapotokat();
    }

    private void OnValidate()
    {
        // Editor módban is azonnal frissüljön az aktív állapot,
        // amikor a checkbox-ot módosítod.
        FrissitsAktivAllapotokat();
    }

    // Futásidőben is átkapcsolható a mód (pl. teszteléshez vagy
    // egy jövőbeli agent-vezérelt kísérlethez).
    public void HaromSzenzorosModBeallitasa(bool ujMod)
    {
        haromSzenzorosMod = ujMod;
        FrissitsAktivAllapotokat();
    }

    private void FrissitsAktivAllapotokat()
    {
        if (balSzenzor != null)
        {
            balSzenzor.gameObject.SetActive(haromSzenzorosMod);
        }
        if (jobbSzenzor != null)
        {
            jobbSzenzor.gameObject.SetActive(haromSzenzorosMod);
        }
        // A középső szenzor mindkét módban aktív marad.
        if (kozepSzenzor != null)
        {
            kozepSzenzor.gameObject.SetActive(true);
        }
    }
}