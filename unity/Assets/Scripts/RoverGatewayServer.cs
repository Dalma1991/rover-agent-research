using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class RoverGatewayServer : MonoBehaviour
{
    [SerializeField, Range(1, 65535)]
    private int port = 8765;

    [SerializeField, Min(256)]
    private int maximalisUzenethossz = 16 * 1024;

    private readonly ConcurrentQueue<FuggobenLevoKeres> keresek =
        new ConcurrentQueue<FuggobenLevoKeres>();

    private readonly ConcurrentQueue<string> naploUzenetek =
        new ConcurrentQueue<string>();

    private readonly object kliensekZar = new object();
    private readonly List<TcpClient> aktivKliensek = new List<TcpClient>();

    private Rigidbody rigidBody;
    private TcpListener listener;
    private Thread listenerSzal;
    private volatile bool fut;

    private Vector3 mozgasIranya;
    private float hatralevoTavolsag;
    private float maximalisSebesseg;

    [Serializable]
    private class KeresUzenet
    {
        public string request_id;
        public string command;
        public float distance_m;
        public float max_speed;
    }

    [Serializable]
    private class AlapValasz
    {
        public string request_id;
        public string status;
        public string message;
    }

    [Serializable]
    private class Pozicio
    {
        public float x;
        public float y;
        public float z;

        public Pozicio(Vector3 ertek)
        {
            x = ertek.x;
            y = ertek.y;
            z = ertek.z;
        }
    }

    [Serializable]
    private class ObserveValasz
    {
        public string request_id;
        public string status;
        public Pozicio position;
        public float speed;
    }

    private sealed class FuggobenLevoKeres
    {
        public readonly string Json;
        public readonly ManualResetEventSlim Elkeszult = new ManualResetEventSlim(false);
        public string Valasz;

        public FuggobenLevoKeres(string json)
        {
            Json = json;
        }
    }

    private void Awake()
    {
        rigidBody = GetComponent<Rigidbody>();
    }

    private void OnEnable()
    {
        InditSzerver();
    }

    private void Update()
    {
        while (naploUzenetek.TryDequeue(out string uzenet))
        {
            Debug.Log(uzenet, this);
        }
    }

    private void FixedUpdate()
    {
        while (keresek.TryDequeue(out FuggobenLevoKeres keres))
        {
            string valasz = FeldolgozKeres(keres.Json);
            keres.Valasz = valasz;

            Debug.Log($"TCP kérés: {keres.Json}\nTCP válasz: {valasz}", this);
            keres.Elkeszult.Set();
        }

        MozgatRover();
    }

    private void OnDisable()
    {
        LeallitSzerver();
    }

    private void OnApplicationQuit()
    {
        LeallitSzerver();
    }

    private void InditSzerver()
    {
        if (fut)
        {
            return;
        }

        fut = true;
        listenerSzal = new Thread(ListenerCiklus)
        {
            IsBackground = true,
            Name = "RoverGateway TCP listener"
        };
        listenerSzal.Start();
    }

    private void ListenerCiklus()
    {
        try
        {
            listener = new TcpListener(IPAddress.Loopback, port);
            listener.Start();
            naploUzenetek.Enqueue($"RoverGateway figyel: 127.0.0.1:{port}");

            while (fut)
            {
                TcpClient kliens = listener.AcceptTcpClient();

                lock (kliensekZar)
                {
                    aktivKliensek.Add(kliens);
                }

                Thread kliensSzal = new Thread(() => KliensKezelo(kliens))
                {
                    IsBackground = true,
                    Name = "RoverGateway TCP client"
                };
                kliensSzal.Start();
            }
        }
        catch (SocketException hiba)
        {
            if (fut)
            {
                naploUzenetek.Enqueue($"RoverGateway hálózati hiba: {hiba.Message}");
            }
        }
        catch (Exception hiba)
        {
            naploUzenetek.Enqueue($"RoverGateway szerverhiba: {hiba.Message}");
        }
        finally
        {
            try
            {
                listener?.Stop();
            }
            catch (SocketException)
            {
                // A listener egy másik szálon már leállhatott.
            }
        }
    }

    private void KliensKezelo(TcpClient kliens)
    {
        try
        {
            kliens.NoDelay = true;

            using (kliens)
            using (NetworkStream halozat = kliens.GetStream())
            using (StreamReader olvaso = new StreamReader(halozat, Encoding.UTF8))
            using (StreamWriter iro = new StreamWriter(halozat, new UTF8Encoding(false))
            {
                AutoFlush = true,
                NewLine = "\n"
            })
            {
                string sor;
                while (fut && (sor = olvaso.ReadLine()) != null)
                {
                    if (sor.Length > maximalisUzenethossz)
                    {
                        // Nem használunk JsonUtilityt a háttérszálon.
                        iro.WriteLine(
                            "{\"request_id\":\"\",\"status\":\"error\","
                            + "\"message\":\"Az üzenet túl hosszú.\"}"
                        );
                        continue;
                    }

                    FuggobenLevoKeres keres = new FuggobenLevoKeres(sor);
                    keresek.Enqueue(keres);

                    // A hálózati szál addig vár, amíg a Unity fő szála elkészíti
                    // az állapotot tartalmazó választ a FixedUpdate-ben.
                    while (fut && !keres.Elkeszult.Wait(100))
                    {
                        // Rövid időközönként ellenőrizzük a leállítási jelzőt is.
                    }

                    if (!fut && string.IsNullOrEmpty(keres.Valasz))
                    {
                        break;
                    }

                    iro.WriteLine(keres.Valasz);
                }
            }
        }
        catch (IOException hiba)
        {
            if (fut)
            {
                naploUzenetek.Enqueue($"RoverGateway klienskapcsolati hiba: {hiba.Message}");
            }
        }
        catch (Exception hiba)
        {
            if (fut)
            {
                naploUzenetek.Enqueue($"RoverGateway klienshiba: {hiba.Message}");
            }
        }
        finally
        {
            lock (kliensekZar)
            {
                aktivKliensek.Remove(kliens);
            }
        }
    }

    private string FeldolgozKeres(string json)
    {
        KeresUzenet keres;

        try
        {
            keres = JsonUtility.FromJson<KeresUzenet>(json);
        }
        catch (ArgumentException)
        {
            return HibaValasz("", "Hibás JSON.");
        }

        if (keres == null)
        {
            return HibaValasz("", "Hibás JSON.");
        }

        if (string.IsNullOrWhiteSpace(keres.request_id))
        {
            return HibaValasz("", "A request_id mező kötelező.");
        }

        switch (keres.command)
        {
            case "observe":
                return JsonUtility.ToJson(new ObserveValasz
                {
                    request_id = keres.request_id,
                    status = "ok",
                    position = new Pozicio(rigidBody.position),
                    speed = rigidBody.linearVelocity.magnitude
                });

            case "move":
                if (keres.distance_m < 0f || keres.max_speed <= 0f
                    || float.IsNaN(keres.distance_m) || float.IsNaN(keres.max_speed)
                    || float.IsInfinity(keres.distance_m) || float.IsInfinity(keres.max_speed))
                {
                    return HibaValasz(
                        keres.request_id,
                        "A distance_m nem lehet negatív, a max_speed pedig legyen pozitív."
                    );
                }

                mozgasIranya = transform.forward.normalized;
                hatralevoTavolsag = keres.distance_m;
                maximalisSebesseg = keres.max_speed;

                return OkValasz(keres.request_id, "A mozgatási parancs elfogadva.");

            case "stop":
                hatralevoTavolsag = 0f;
                maximalisSebesseg = 0f;

                return OkValasz(keres.request_id, "A gömb megállt.");

            default:
                return HibaValasz(keres.request_id, "Ismeretlen parancs.");
        }
    }

    private void MozgatRover()
    {
        if (hatralevoTavolsag <= 0f || maximalisSebesseg <= 0f)
        {
            return;
        }

        float lepes = Mathf.Min(
            maximalisSebesseg * Time.fixedDeltaTime,
            hatralevoTavolsag
        );

        rigidBody.MovePosition(rigidBody.position + mozgasIranya * lepes);
        hatralevoTavolsag -= lepes;

        if (hatralevoTavolsag <= Mathf.Epsilon)
        {
            hatralevoTavolsag = 0f;
            maximalisSebesseg = 0f;
        }
    }

    private string OkValasz(string requestId, string uzenet)
    {
        return JsonUtility.ToJson(new AlapValasz
        {
            request_id = requestId,
            status = "ok",
            message = uzenet
        });
    }

    private string HibaValasz(string requestId, string uzenet)
    {
        return JsonUtility.ToJson(new AlapValasz
        {
            request_id = requestId,
            status = "error",
            message = uzenet
        });
    }

    private void LeallitSzerver()
    {
        if (!fut)
        {
            return;
        }

        fut = false;

        try
        {
            listener?.Stop();
        }
        catch (SocketException)
        {
            // A listener leállításakor ez ártalmatlan versenyhelyzet lehet.
        }

        lock (kliensekZar)
        {
            foreach (TcpClient kliens in aktivKliensek.ToArray())
            {
                kliens.Close();
            }

            aktivKliensek.Clear();
        }

        while (keresek.TryDequeue(out FuggobenLevoKeres keres))
        {
            keres.Valasz = null;
            keres.Elkeszult.Set();
        }

        if (listenerSzal != null && listenerSzal.IsAlive)
        {
            listenerSzal.Join(1000);
        }

        listenerSzal = null;
        listener = null;
    }
}
