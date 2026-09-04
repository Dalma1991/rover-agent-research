using System.Collections;
using NUnit.Framework;
#if UNITY_EDITOR
using UnityEditor.SceneManagement;
#endif
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

// M11 3. munkacsomag: Play Mode tesztek a TrackScene-en.
// A jelenetet a Build Settings-tol fuggetlenul, utvonal alapjan toltjuk be.
public class TrackSceneTeszt
{
    private const string JelenetUtvonal = "Assets/Scenes/TrackScene.unity";

    [UnitySetUp]
    public IEnumerator JelenetBetoltese()
    {
#if UNITY_EDITOR
        EditorSceneManager.LoadSceneInPlayMode(JelenetUtvonal, new LoadSceneParameters(LoadSceneMode.Single));
#else
        Assert.Ignore("A TrackScene betoltese csak az Editorban tamogatott.");
#endif
        yield return null;                       // a jelenet objektumai letrejonnek
        yield return new WaitForFixedUpdate();   // az elso FixedUpdate-es meresek lefutnak
        yield return new WaitForFixedUpdate();
    }

    [UnityTest]
    public IEnumerator Jelenet_TartalmazzaAKotelezoKomponenseket()
    {
        Assert.IsNotNull(Object.FindFirstObjectByType<TrackController>(), "Hianyzik a TrackController.");
        Assert.IsNotNull(Object.FindFirstObjectByType<SensorArray>(), "Hianyzik a SensorArray.");
        Assert.IsNotNull(Object.FindFirstObjectByType<LidarSensor>(), "Hianyzik a LidarSensor.");
        Assert.IsNotNull(Object.FindFirstObjectByType<RoverGatewayServer>(), "Hianyzik a RoverGatewayServer.");
        yield return null;
    }

    [UnityTest]
    public IEnumerator Lidar_ABeallitottSugarszammalMer()
    {
        LidarSensor lidar = Object.FindFirstObjectByType<LidarSensor>();
        Assert.IsNotNull(lidar.NyersTavolsagok, "A Lidar meg nem mert.");
        Assert.AreEqual(lidar.SugarSzam, lidar.NyersTavolsagok.Length);
        Assert.AreEqual(lidar.SugarSzam, lidar.ErvenyessegiMaszk.Length);
        foreach (float tav in lidar.NyersTavolsagok)
        {
            Assert.That(tav, Is.InRange(0f, lidar.MaxHatotav));
        }
        yield return null;
    }

    [UnityTest]
    public IEnumerator KozepSzenzor_KonzisztensAPalyageometriaval()
    {
        // M07 kalibracio regresszios tesztje: ha a palya-geometria szerint a
        // kozepso szenzor a vonalon van, a szinszenzornak feheret kell latnia,
        // es forditva.
        TrackController palya = Object.FindFirstObjectByType<TrackController>();
        SensorArray szenzorok = Object.FindFirstObjectByType<SensorArray>();
        ColorSensor kozep = null;
        foreach (ColorSensor cs in szenzorok.GetComponentsInChildren<ColorSensor>())
        {
            if (cs.name == "SensorCenter") { kozep = cs; }
        }
        Assert.IsNotNull(kozep, "Nincs SensorCenter a SensorArray alatt.");
        Assert.IsTrue(kozep.ErvenyesMeres, "A kozepso szenzor nem adott ervenyes merest.");

        bool geometriaSzerintVonalon = palya.TavolsagAKozepvonaltol(kozep.transform.position, out float tav);
        Assert.AreEqual(
            geometriaSzerintVonalon, kozep.FeherVonalon,
            $"Geometria: {tav:F3} m a kozepvonaltol (vonalon={geometriaSzerintVonalon}), szenzor FeherVonalon={kozep.FeherVonalon}."
        );
        yield return null;
    }
}
