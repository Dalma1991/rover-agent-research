using System;
using System.Diagnostics;
using UnityEngine;
using Debug = UnityEngine.Debug;

// M08: 2D LiDAR-szimuláció. Ezt a scriptet Claude írta (nem Codex),
// lásd AI_USAGE.md.
//
// Működés:
// - A transform.forward körül, vízszintes síkban, Latomezo fokos
//   látómezőben, SugarSzam db egyenletesen elosztott raycastet indít.
// - Minden sugárhoz nyers távolságot és érvényességi jelzőt ad vissza
//   (NyersTavolsagok / ErvenyessegiMaszk), MaxHatotav-val korlátozva.
// - A nyers sugarakat SzektorSzam db szektorba csoportosítja, és
//   szektoronként Min/Átlag távolságot számol (kompressziós
//   alternatíva a nyers jelhez képest).
// - Zaj (Gauss, seedelt), soronkénti méréskimaradás, mesterséges
//   késleltetés és ritkított frissítés szimulálja egy valódi LiDAR
//   korlátait.
// - Profilozáshoz minden mérés idejét (Stopwatch) méri, és
//   UtolsoMeresIdejeMs / AtlagMeresIdejeMs property-ken keresztül
//   elérhető.
public class LidarSensor : MonoBehaviour
{
    [Header("Geometriai beállítások")]
    [Tooltip("A látómező szélessége fokban, a transform.forward körül szimmetrikusan")]
    [SerializeField]
    private float latomezoFok = 180f;
    [Tooltip("A látómezőben egyenletesen elosztott sugarak száma")]
    [SerializeField, Min(1)]
    private int sugarSzam = 36;
    [SerializeField]
    private float maxHatotav = 10f;
    [SerializeField]
    private float raycastMagassag = 0.15f;
    [SerializeField]
    private LayerMask akadalyReteg = ~0;

    [Header("Szektoros tömörítés")]
    [Tooltip("Hány szektorba legyenek csoportosítva a nyers sugarak (0 = nincs tömörítés)")]
    [SerializeField, Min(0)]
    private int szektorSzam = 6;

    [Header("Zaj- és bizonytalanság-paraméterek")]
    [Tooltip("Gauss-zaj szórása a mért távolságon, méterben (0 = nincs zaj)")]
    [SerializeField]
    private float zajSzorasMeter = 0.02f;
    [Tooltip("Egy adott sugár kimaradásának valószínűsége (0-1)")]
    [SerializeField]
    private float meresKimaradasEselye = 0.0f;
    [Tooltip("Mérési késés FixedUpdate keretekben (0 = nincs késés)")]
    [SerializeField]
    private int kesesFixedUpdateKeretekben = 0;
    [Tooltip("Csak minden N. FixedUpdate-ben frissül (1 = minden keretben)")]
    [SerializeField, Min(1)]
    private int frissitesRitkitasa = 1;
    [Tooltip("A zajgenerátor seedje - azonos seed = azonos zajsorozat")]
    [SerializeField]
    private int zajSeed = 22222;

    [Header("Debug")]
    [SerializeField]
    private bool debugMegjelenites = true;

    // --- Nyers, sugáronkénti kimenet ---
    public float[] NyersTavolsagok { get; private set; }
    public bool[] ErvenyessegiMaszk { get; private set; }
    public float MaxHatotav => maxHatotav;
    public int SugarSzam => sugarSzam;
        public float KozepSugarTavolsag()
    {
        if (NyersTavolsagok == null || NyersTavolsagok.Length == 0)
        {
            return -1f;
        }
        int kozepIndex = Mathf.RoundToInt((sugarSzam - 1) / 2f);
        return NyersTavolsagok[kozepIndex];
    }

    // --- Szektoros, tömörített kimenet ---
    public float[] SzektorMinTavolsag { get; private set; }
    public float[] SzektorAtlagTavolsag { get; private set; }

    // --- Profilozás ---
    public double UtolsoMeresIdejeMs { get; private set; }
    public double AtlagMeresIdejeMs => meresekSzama > 0 ? osszesMeresIdoMs / meresekSzama : 0.0;

    private System.Random veletlenszamGenerator;
    private float[][] keslelteteesPuffer;
    private int pufferIndex;
    private int fixedUpdateSzamlalo;
    private readonly Stopwatch stopwatch = new Stopwatch();
    private double osszesMeresIdoMs;
    private long meresekSzama;

    private void Awake()
    {
        veletlenszamGenerator = new System.Random(zajSeed);
        NyersTavolsagok = new float[sugarSzam];
        ErvenyessegiMaszk = new bool[sugarSzam];

        int pufferMeret = Mathf.Max(1, kesesFixedUpdateKeretekben + 1);
        keslelteteesPuffer = new float[pufferMeret][];
        for (int i = 0; i < pufferMeret; i++)
        {
            keslelteteesPuffer[i] = new float[sugarSzam];
        }
        pufferIndex = 0;

        if (szektorSzam > 0)
        {
            SzektorMinTavolsag = new float[szektorSzam];
            SzektorAtlagTavolsag = new float[szektorSzam];
        }
    }

    private void FixedUpdate()
    {
        fixedUpdateSzamlalo++;
        if (fixedUpdateSzamlalo % frissitesRitkitasa != 0)
        {
            return;
        }

        stopwatch.Restart();
        MeresVegrehajtasa();
        stopwatch.Stop();

        UtolsoMeresIdejeMs = stopwatch.Elapsed.TotalMilliseconds;
        osszesMeresIdoMs += UtolsoMeresIdejeMs;
        meresekSzama++;
    }

    private void MeresVegrehajtasa()
    {
        Vector3 kozeppont = transform.position + Vector3.up * raycastMagassag;
        float[] friss = keslelteteesPuffer[pufferIndex];

        for (int i = 0; i < sugarSzam; i++)
        {
            float szog = SugarSzoge(i);
            Vector3 irany = Quaternion.AngleAxis(szog, Vector3.up) * transform.forward;

            bool kimarad = veletlenszamGenerator.NextDouble() < meresKimaradasEselye;
            if (kimarad)
            {
                friss[i] = -1f;
                continue;
            }

            bool talalat = Physics.Raycast(
                kozeppont, irany, out RaycastHit hitInfo, maxHatotav, akadalyReteg
            );

            float tavolsag = talalat ? hitInfo.distance : -1f;
            if (talalat && zajSzorasMeter > 0f)
            {
                float zaj = KovetkezoGaussZaj() * zajSzorasMeter;
                tavolsag = Mathf.Clamp(tavolsag + zaj, 0f, maxHatotav);
            }
            friss[i] = tavolsag;
        }

        pufferIndex = (pufferIndex + 1) % keslelteteesPuffer.Length;
        float[] kiadott = keslelteteesPuffer[pufferIndex];

        for (int i = 0; i < sugarSzam; i++)
        {
            bool ervenyes = kiadott[i] >= 0f;
            NyersTavolsagok[i] = ervenyes ? kiadott[i] : maxHatotav;
            ErvenyessegiMaszk[i] = ervenyes;
        }

        if (szektorSzam > 0)
        {
            SzektorokSzamitasa();
        }
    }

    // A -latomezoFok/2 .. +latomezoFok/2 tartományt egyenletesen osztja
    // fel sugarSzam db irányra; 1 sugár esetén pontosan előre néz.
    private float SugarSzoge(int index)
    {
        if (sugarSzam == 1)
        {
            return 0f;
        }
        float t = (float)index / (sugarSzam - 1);
        return Mathf.Lerp(-latomezoFok / 2f, latomezoFok / 2f, t);
    }

    private void SzektorokSzamitasa()
    {
        int sugarSzektoronkent = Mathf.Max(1, sugarSzam / szektorSzam);
        for (int s = 0; s < szektorSzam; s++)
        {
            int kezdoIndex = s * sugarSzektoronkent;
            int vegIndex = (s == szektorSzam - 1) ? sugarSzam : kezdoIndex + sugarSzektoronkent;

            float min = maxHatotav;
            float osszeg = 0f;
            int darab = 0;

            for (int i = kezdoIndex; i < vegIndex && i < sugarSzam; i++)
            {
                if (!ErvenyessegiMaszk[i])
                {
                    continue;
                }
                min = Mathf.Min(min, NyersTavolsagok[i]);
                osszeg += NyersTavolsagok[i];
                darab++;
            }

            SzektorMinTavolsag[s] = darab > 0 ? min : maxHatotav;
            SzektorAtlagTavolsag[s] = darab > 0 ? osszeg / darab : maxHatotav;
        }
    }

    private float KovetkezoGaussZaj()
    {
        double u1 = 1.0 - veletlenszamGenerator.NextDouble();
        double u2 = veletlenszamGenerator.NextDouble();
        double normal = Math.Sqrt(-2.0 * Math.Log(u1)) * Math.Sin(2.0 * Math.PI * u2);
        return (float)normal;
    }

    private void OnDrawGizmos()
    {
        if (!debugMegjelenites || NyersTavolsagok == null)
        {
            return;
        }

        Vector3 kozeppont = transform.position + Vector3.up * raycastMagassag;

        for (int i = 0; i < sugarSzam; i++)
        {
            float szog = SugarSzoge(i);
            Vector3 irany = Quaternion.AngleAxis(szog, Vector3.up) * transform.forward;
            bool ervenyes = Application.isPlaying && i < ErvenyessegiMaszk.Length && ErvenyessegiMaszk[i];
            float tav = Application.isPlaying ? NyersTavolsagok[i] : maxHatotav;

            Gizmos.color = Application.isPlaying
                ? (ervenyes ? Color.cyan : Color.grey)
                : Color.yellow;
            Gizmos.DrawLine(kozeppont, kozeppont + irany * tav);
        }

#if UNITY_EDITOR
        if (Application.isPlaying)
        {
            UnityEditor.Handles.Label(
                kozeppont + Vector3.up * 0.2f,
                $"LiDAR {sugarSzam} sugár, {UtolsoMeresIdejeMs:F3} ms\nKözépső sugár: {KozepSugarTavolsag():F3} m"
            );
        }
#endif
    }
}