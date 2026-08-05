using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

// Ezt a scriptet Dalma írta kézzel (nem a Codex), mert a hónapos AI-kvóta
// elfogyott az M06 mérföldkő munkája közben. A szcenárió-sémát, a
// generátort és a dokumentációt a Codex készítette (lásd AI_USAGE.md).
//
// Beolvas egy szcenárió JSON fájlt (experiments/scenarios/ mappából),
// felépíti a stadion alakú fehér vonalat, és létrehozza/időzíti az
// akadályokat a schedule mezők alapján.
public class TrackController : MonoBehaviour
{
    [Header("Szcenárió")]
    [SerializeField]
    private string szcenarioFajlNev = "stadium-train-baseline.json";

    [Header("Hivatkozások")]
    [SerializeField]
    private Renderer talajRenderer; // húzd ide a Plane-t az Inspectorban

    private LineRenderer vonalRenderer;
    private ScenarioDokumentum dokumentum;
    private readonly List<AkadalyPeldany> akadalyok = new List<AkadalyPeldany>();

    private const int IvSzegmensSzam = 24; // hány szakaszból áll egy félkör

    [Serializable]
    private class Pont3D
    {
        public float x;
        public float y;
        public float z;

        public Vector3 UnityVektor()
        {
            return new Vector3(x, y, z);
        }
    }

    [Serializable]
    private class Rgb
    {
        public int r;
        public int g;
        public int b;

        public Color UnitySzin()
        {
            return new Color(r / 255f, g / 255f, b / 255f);
        }
    }

    [Serializable]
    private class Utemezes
    {
        public float appear_at_s;
        public float visible_for_s;
        public float disappear_at_s;
    }

    [Serializable]
    private class Akadaly
    {
        public string id;
        public Pont3D position_m;
        public Pont3D size_m;
        public Utemezes schedule;
    }

    [Serializable]
    private class Palya
    {
        public float straight_length_m;
        public float turn_radius_m;
        public float line_width_m;
        public Rgb background_color_rgb;
    }

    [Serializable]
    private class Metaadat
    {
        public string name;
        public string type;
        public uint seed;
    }

    [Serializable]
    private class ScenarioDokumentum
    {
        public string schema_version;
        public Metaadat metadata;
        public Palya track;
        public Akadaly[] obstacles;
    }

    private class AkadalyPeldany
    {
        public GameObject Objektum;
        public float MegjelenesIdo;
        public float EltunesIdo;
    }

    private void Awake()
    {
        vonalRenderer = GetComponent<LineRenderer>();
        if (vonalRenderer == null)
        {
            vonalRenderer = gameObject.AddComponent<LineRenderer>();
        }

        string tartalom = BeolvasSzcenariot(szcenarioFajlNev);
        dokumentum = JsonUtility.FromJson<ScenarioDokumentum>(tartalom);

        if (dokumentum == null || dokumentum.track == null)
        {
            Debug.LogError(
                $"TrackController: nem sikerült beolvasni/értelmezni a "
                + $"'{szcenarioFajlNev}' szcenáriót.",
                this
            );
            return;
        }

        FelepitPalyaVonalat();
        BeallitTalajSzint();
        FelepitAkadalyokat();

        Debug.Log(
            $"TrackController: '{dokumentum.metadata.name}' szcenárió betöltve "
            + $"({dokumentum.obstacles.Length} akadállyal, seed={dokumentum.metadata.seed}).",
            this
        );
    }

    private void Update()
    {
        float t = Time.timeSinceLevelLoad;

        foreach (AkadalyPeldany akadaly in akadalyok)
        {
            bool lathato = t >= akadaly.MegjelenesIdo && t < akadaly.EltunesIdo;
            if (akadaly.Objektum.activeSelf != lathato)
            {
                akadaly.Objektum.SetActive(lathato);
            }
        }
    }

    private string BeolvasSzcenariot(string fajlNev)
    {
        string gyokerMappa = Path.GetFullPath(
            Path.Combine(Application.dataPath, "..", "..")
        );
        string teljesUtvonal = Path.Combine(
            gyokerMappa, "experiments", "scenarios", fajlNev
        );
        return File.ReadAllText(teljesUtvonal);
    }

    private void FelepitPalyaVonalat()
    {
        float felHossz = dokumentum.track.straight_length_m / 2f;
        float sugar = dokumentum.track.turn_radius_m;
        float y = 0.01f; // kicsit a talaj fölött, hogy ne "villogjon"

        List<Vector3> pontok = new List<Vector3>();

        // 1. egyenes: x = +sugar, z: +felHossz -> -felHossz
        pontok.Add(new Vector3(sugar, y, felHossz));
        pontok.Add(new Vector3(sugar, y, -felHossz));

        // hátsó félkör (középpont: 0,0,-felHossz), x=+sugar -> x=-sugar,
        // kifelé (negatív z irányba) domborodva
        Vector3 hatsoKozeppont = new Vector3(0f, y, -felHossz);
        for (int i = 1; i < IvSzegmensSzam; i++)
        {
            float szog = Mathf.Deg2Rad * (90f - i * (180f / IvSzegmensSzam));
            Vector3 pont = hatsoKozeppont + sugar * new Vector3(
                Mathf.Sin(szog), 0f, -Mathf.Cos(szog)
            );
            pontok.Add(pont);
        }

        // 2. egyenes: x = -sugar, z: -felHossz -> +felHossz
        pontok.Add(new Vector3(-sugar, y, -felHossz));
        pontok.Add(new Vector3(-sugar, y, felHossz));

        // első (elülső) félkör (középpont: 0,0,+felHossz), x=-sugar -> x=+sugar,
        // kifelé (pozitív z irányba) domborodva
        Vector3 elsoKozeppont = new Vector3(0f, y, felHossz);
        for (int i = 1; i < IvSzegmensSzam; i++)
        {
            float szog = Mathf.Deg2Rad * (-90f + i * (180f / IvSzegmensSzam));
            Vector3 pont = elsoKozeppont + sugar * new Vector3(
                Mathf.Sin(szog), 0f, Mathf.Cos(szog)
            );
            pontok.Add(pont);
        }

        vonalRenderer.positionCount = pontok.Count;
        vonalRenderer.SetPositions(pontok.ToArray());
        vonalRenderer.loop = true;
        vonalRenderer.widthMultiplier = dokumentum.track.line_width_m;
        vonalRenderer.useWorldSpace = true;

        Shader vonalShader = Shader.Find("Universal Render Pipeline/Unlit")
            ?? Shader.Find("Sprites/Default");
        Material vonalAnyag = new Material(vonalShader);
        BeallitAnyagSzint(vonalAnyag, Color.white);
        vonalRenderer.material = vonalAnyag;
    }

    private void BeallitTalajSzint()
    {
        if (talajRenderer == null)
        {
            Debug.LogWarning(
                "TrackController: nincs beállítva a talajRenderer mező, "
                + "a háttérszín nem lesz alkalmazva.",
                this
            );
            return;
        }

        BeallitAnyagSzint(talajRenderer.material, dokumentum.track.background_color_rgb.UnitySzin());
    }

    private void BeallitAnyagSzint(Material anyag, Color szin)
    {
        if (anyag.HasProperty("_BaseColor"))
        {
            anyag.SetColor("_BaseColor", szin);
        }
        else if (anyag.HasProperty("_Color"))
        {
            anyag.SetColor("_Color", szin);
        }
    }

    private void FelepitAkadalyokat()
    {
        foreach (Akadaly akadaly in dokumentum.obstacles)
        {
            GameObject objektum = GameObject.CreatePrimitive(PrimitiveType.Cube);
            objektum.name = akadaly.id;
            objektum.transform.SetParent(transform);
            objektum.transform.position = akadaly.position_m.UnityVektor();
            objektum.transform.localScale = akadaly.size_m.UnityVektor();
            objektum.SetActive(false);

            akadalyok.Add(new AkadalyPeldany
            {
                Objektum = objektum,
                MegjelenesIdo = akadaly.schedule.appear_at_s,
                EltunesIdo = akadaly.schedule.disappear_at_s,
            });
        }
    }
// --- M07: nyilvános geometriai lekérdezés a szenzorokhoz ---
    //
    // Visszaadja, hogy egy adott világkoordináta (XZ síkban vetítve)
    // mekkora távolságra van a pálya középvonalától (méterben), valamint
    // hogy ez a táv a vonal félszélességén belül van-e ("a vonalon van").
    public bool TavolsagAKozepvonaltol(Vector3 vilagPoziicio, out float tavolsagM)
    {
        if (dokumentum == null || dokumentum.track == null)
        {
            tavolsagM = float.PositiveInfinity;
            return false;
        }

        float felHossz = dokumentum.track.straight_length_m / 2f;
        float sugar = dokumentum.track.turn_radius_m;
        float felSzelesseg = dokumentum.track.line_width_m / 2f;

        float x = vilagPoziicio.x;
        float z = vilagPoziicio.z;

        float legkisebbTavolsag = float.PositiveInfinity;

        legkisebbTavolsag = Mathf.Min(
            legkisebbTavolsag,
            TavolsagEgyenestol(x, z, sugar, -felHossz, felHossz)
        );

        legkisebbTavolsag = Mathf.Min(
            legkisebbTavolsag,
            TavolsagEgyenestol(x, z, -sugar, -felHossz, felHossz)
        );

        legkisebbTavolsag = Mathf.Min(
            legkisebbTavolsag,
            TavolsagIvtol(x, z, 0f, -felHossz, sugar)
        );

        legkisebbTavolsag = Mathf.Min(
            legkisebbTavolsag,
            TavolsagIvtol(x, z, 0f, felHossz, sugar)
        );

        tavolsagM = legkisebbTavolsag;
        return legkisebbTavolsag <= felSzelesseg;
    }

    private float TavolsagEgyenestol(float x, float z, float allandoX, float z1, float z2)
    {
        float zClamp = Mathf.Clamp(z, Mathf.Min(z1, z2), Mathf.Max(z1, z2));
        float dx = x - allandoX;
        float dz = z - zClamp;
        return Mathf.Sqrt(dx * dx + dz * dz);
    }

    private float TavolsagIvtol(float x, float z, float kozepX, float kozepZ, float sugar)
    {
        float dx = x - kozepX;
        float dz = z - kozepZ;
        float tavKozepponttol = Mathf.Sqrt(dx * dx + dz * dz);
        return Mathf.Abs(tavKozepponttol - sugar);
    }

    public float VonalFelSzelessegeM
    {
        get
        {
            if (dokumentum == null || dokumentum.track == null)
            {
                return 0.1f;
            }
            return dokumentum.track.line_width_m / 2f;
        }
    }}