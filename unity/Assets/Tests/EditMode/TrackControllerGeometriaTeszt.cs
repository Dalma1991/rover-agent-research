using NUnit.Framework;
using UnityEngine;

// M11 3. munkacsomag: Edit Mode tesztek a palya-geometriara.
// A TrackController [ExecuteAlways], ezert AddComponent-kor Edit modban is
// lefut az Awake es betolti a stadium-train-baseline.json szcenariot
// (straight_length_m=12, turn_radius_m=4, line_width_m=0.18).
public class TrackControllerGeometriaTeszt
{
    private GameObject objektum;
    private TrackController palya;

    private const float FelHossz = 6f;      // 12 / 2
    private const float Sugar = 4f;
    private const float FelSzelesseg = 0.09f; // 0.18 / 2

    [SetUp]
    public void Elokeszit()
    {
        objektum = new GameObject("TesztTrackController");
        palya = objektum.AddComponent<TrackController>();
    }

    [TearDown]
    public void Takarit()
    {
        Object.DestroyImmediate(objektum);
    }

    [Test]
    public void EgyenesSzakaszKozepvonalan_NullaTavolsag_VonalonVan()
    {
        bool vonalon = palya.TavolsagAKozepvonaltol(new Vector3(Sugar, 0f, 0f), out float tav);
        Assert.That(tav, Is.EqualTo(0f).Within(1e-4f));
        Assert.IsTrue(vonalon);
    }

    [Test]
    public void IvKozepvonalan_NullaTavolsag_VonalonVan()
    {
        // A felso felkor kozeppontja (0, FelHossz), sugara Sugar -> a
        // (0, FelHossz + Sugar) pont pontosan az iven van.
        bool vonalon = palya.TavolsagAKozepvonaltol(new Vector3(0f, 0f, FelHossz + Sugar), out float tav);
        Assert.That(tav, Is.EqualTo(0f).Within(1e-4f));
        Assert.IsTrue(vonalon);
    }

    [Test]
    public void PalyaKozepen_TavolVan_NincsVonalon()
    {
        bool vonalon = palya.TavolsagAKozepvonaltol(Vector3.zero, out float tav);
        Assert.That(tav, Is.EqualTo(Sugar).Within(1e-4f));
        Assert.IsFalse(vonalon);
    }

    [Test]
    public void FantomIv_AStadionBelsejeben_NincsVonalon()
    {
        // Regresszios teszt: a felso felkor (kozeppont (0, FelHossz)) also,
        // nem letezo fele a (0, FelHossz - Sugar) = (0, 2) ponton menne at.
        // A javitas elott itt 0 tavolsag es "vonalon" jott vissza.
        bool vonalon = palya.TavolsagAKozepvonaltol(new Vector3(0f, 0f, FelHossz - Sugar), out float tav);
        Assert.IsFalse(vonalon, "A stadion belsejeben nincs vonal.");
        Assert.That(tav, Is.EqualTo(Sugar).Within(1e-4f));

        bool vonalonAlul = palya.TavolsagAKozepvonaltol(new Vector3(0f, 0f, -(FelHossz - Sugar)), out float tavAlul);
        Assert.IsFalse(vonalonAlul);
        Assert.That(tavAlul, Is.EqualTo(Sugar).Within(1e-4f));
    }

    [Test]
    public void VonalSzelessegKuszob_BelulIgen_KivulNem()
    {
        bool belul = palya.TavolsagAKozepvonaltol(new Vector3(Sugar + FelSzelesseg - 0.005f, 0f, 1f), out _);
        bool kivul = palya.TavolsagAKozepvonaltol(new Vector3(Sugar + FelSzelesseg + 0.005f, 0f, 1f), out _);
        Assert.IsTrue(belul, "A felszelessegen belul a vonalon kell lennie.");
        Assert.IsFalse(kivul, "A felszelessegen kivul nem lehet a vonalon.");
    }
}
