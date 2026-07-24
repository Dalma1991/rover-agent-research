using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

public class MovementControllerPlayModeTests
{
    private GameObject gomb;
    private Rigidbody rigidBody;
    private MovementController controller;

    [UnitySetUp]
    public IEnumerator SetUp()
    {
        gomb = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        rigidBody = gomb.AddComponent<Rigidbody>();
        rigidBody.useGravity = false;
        rigidBody.constraints = RigidbodyConstraints.FreezeRotation;

        controller = gomb.AddComponent<MovementController>();

        // A tesztek közvetlenül hívják a publikus metódusokat, ezért a komponens
        // saját Update/FixedUpdate ciklusát kikapcsoljuk a teszt idejére.
        controller.enabled = false;

        yield return null;
    }

    [UnityTearDown]
    public IEnumerator TearDown()
    {
        Object.Destroy(gomb);
        yield return null;
    }

    [UnityTest]
    public IEnumerator Move_JobbraMozditjaAGombot()
    {
        Vector3 kezdoPozicio = rigidBody.position;

        controller.Move(Vector2.right);
        yield return new WaitForFixedUpdate();

        Assert.Greater(
            rigidBody.position.x,
            kezdoPozicio.x,
            "A gömb X pozíciójának növekednie kellett volna."
        );
        Assert.That(rigidBody.position.z, Is.EqualTo(kezdoPozicio.z).Within(0.0001f));
    }

    [UnityTest]
    public IEnumerator ResetPosition_VisszaallitjaAKezdoPoziciot()
    {
        Vector3 kezdoPozicio = rigidBody.position;

        rigidBody.position = new Vector3(3f, 1f, -2f);
        rigidBody.linearVelocity = new Vector3(1f, 0f, 1f);
        Physics.SyncTransforms();

        controller.ResetPosition();
        yield return new WaitForFixedUpdate();

        Assert.That(rigidBody.position, Is.EqualTo(kezdoPozicio));
        Assert.That(rigidBody.linearVelocity, Is.EqualTo(Vector3.zero));
    }
}
