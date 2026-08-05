using System;
using UnityEngine;

// M07: alsó színérzékelő (fehér vonal érzékelése), kontrollált
// bizonytalansággal. Ezt a scriptet Claude írta (nem Codex), mert a
// projekt jelenleg Codex-kvóta nélkül halad tovább - lásd AI_USAGE.md.
public class ColorSensor : MonoBehaviour
{
    [Header("Pálya hivatkozás")]
    [SerializeField]
    private TrackController palya;

    [Header("Raycast beállítások")]
    [SerializeField]
    private float raycastMagassag = 0.5f;
    [SerializeField]
    private float raycastTavolsag = 1.0f;
    [SerializeField]
    private LayerMask talajReteg = ~0;

    [Header("Zaj- és bizonytalanság-paraméterek")]
    [Tooltip("Gauss-zaj szórása az intenzitáson (0 = nincs zaj)")]
    [SerializeField]
    private float zajSzoras = 0.05f;
    [Tooltip("Bináris white/not_white döntés küszöbe (0-1 skálán)")]
    [SerializeField]
    private float kuszob = 0.5f;
    [Tooltip("Mérési késés FixedUpdate keretekben (0 = nincs késés)")]
    [SerializeField]
    private int kesesFixedUpdateKeretekben = 0;
    [Tooltip("Egy adott mérés kimaradásának valószínűsége (0-1)")]
    [SerializeField]
    private float meresKimaradasValoszinusege = 0.0f;
    [Tooltip("A zajgenerátor seedje - azonos seed = azonos zajsorozat")]
    [SerializeField]
    private int zajSeed = 12345;

    [Header("Debug")]
    [SerializeField]
    private bool debugMegjelenites = true;

    public float NyersIntenzitas { get; private set; }
    public float MertIntenzitas { get; private set; }
    public bool FeherVonalon { get; private set; }
    public bool ErvenyesMeres { get; private set; }
    public Vector3 UtolsoTalalatiPont { get; private set; }

    private System.Random veletlenszamGenerator;
    private float[] keslelteteesPuffer;
    private int pufferIndex;

    private void Awake()
    {
        veletlenszamGenerator = new System.Random(zajSeed);
        int pufferMeret = Mathf.Max(1, kesesFixedUpdateKeretekben + 1);
        keslelteteesPuffer = new float[pufferMeret];
        pufferIndex = 0;
    }

    private void FixedUpdate()
    {
        MeresVegrehajtasa();
    }

    private void MeresVegrehajtasa()
    {
        Vector3 sugarKezdete = transform.position + Vector3.up * raycastMagassag;
        bool talalat = Physics.Raycast(
            sugarKezdete, Vector3.down, out RaycastHit hitInfo,
            raycastTavolsag + raycastMagassag, talajReteg
        );

        float valodiIntenzitas = 0f;
        if (talalat)
        {
            UtolsoTalalatiPont = hitInfo.point;
            if (palya != null)
            {
                palya.TavolsagAKozepvonaltol(hitInfo.point, out float tav);
                valodiIntenzitas = FolytonosIntenzitas(tav);
            }
        }

        NyersIntenzitas = valodiIntenzitas;

        bool kimarad = veletlenszamGenerator.NextDouble() < meresKimaradasValoszinusege;

        if (!kimarad)
        {
            float zaj = KovetkezoGaussZaj() * zajSzoras;
            float zajosIntenzitas = Mathf.Clamp01(valodiIntenzitas + zaj);
            keslelteteesPuffer[pufferIndex] = zajosIntenzitas;
            pufferIndex = (pufferIndex + 1) % keslelteteesPuffer.Length;
        }

        MertIntenzitas = keslelteteesPuffer[pufferIndex];
        FeherVonalon = MertIntenzitas >= kuszob;
        ErvenyesMeres = !kimarad;
    }

    private float FolytonosIntenzitas(float tavolsagAKozepvonaltol)
    {
        float felSzelesseg = palya != null ? palya.VonalFelSzelessegeM : 0.1f;
        const float lecsengesSav = 0.1f;

        if (tavolsagAKozepvonaltol <= felSzelesseg)
        {
            return 1f;
        }

        float tulcsordulas = tavolsagAKozepvonaltol - felSzelesseg;
        return 1f - Mathf.Clamp01(tulcsordulas / lecsengesSav);
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
        if (!debugMegjelenites)
        {
            return;
        }

        Vector3 sugarKezdete = transform.position + Vector3.up * raycastMagassag;
        Gizmos.color = Color.yellow;
        Gizmos.DrawLine(sugarKezdete, sugarKezdete + Vector3.down * (raycastTavolsag + raycastMagassag));

        if (Application.isPlaying)
        {
            Gizmos.color = FeherVonalon ? Color.white : Color.red;
            Gizmos.DrawSphere(UtolsoTalalatiPont, 0.03f);

#if UNITY_EDITOR
            UnityEditor.Handles.Label(
                UtolsoTalalatiPont + Vector3.up * 0.1f,
                $"I={MertIntenzitas:F2} {(FeherVonalon ? "WHITE" : "not_white")}{(ErvenyesMeres ? "" : " (dropout)")}"
            );
#endif
        }
    }
}