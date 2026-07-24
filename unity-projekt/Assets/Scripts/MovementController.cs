using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class MovementController : MonoBehaviour
{
    [SerializeField, Min(0f)]
    private float sebesseg = 5f;

    private Rigidbody rigidBody;
    private Vector3 kezdoPozicio;
    private Quaternion kezdoForgatas;
    private Vector2 mozgasBemenet;
    private bool resetKerve;

    private void Awake()
    {
        rigidBody = GetComponent<Rigidbody>();
        kezdoPozicio = rigidBody.position;
        kezdoForgatas = rigidBody.rotation;
    }

    private void Update()
    {
        // A Horizontal és Vertical tengelyek alapból a WASD és a nyílbillentyűk
        // bemenetét is kezelik a klasszikus Unity Input Managerben.
        mozgasBemenet = new Vector2(
            Input.GetAxisRaw("Horizontal"),
            Input.GetAxisRaw("Vertical")
        ).normalized;

        if (Input.GetKeyDown(KeyCode.R))
        {
            resetKerve = true;
        }
    }

    private void FixedUpdate()
    {
        if (resetKerve)
        {
            ResetPosition();
            resetKerve = false;
            return;
        }

        Vector3 mozgasIranya = new Vector3(mozgasBemenet.x, 0f, mozgasBemenet.y);
        Vector3 ujPozicio = rigidBody.position
                            + mozgasIranya * sebesseg * Time.fixedDeltaTime;

        rigidBody.MovePosition(ujPozicio);
    }

    public void ResetPosition()
    {
        rigidBody.linearVelocity = Vector3.zero;
        rigidBody.angularVelocity = Vector3.zero;
        rigidBody.position = kezdoPozicio;
        rigidBody.rotation = kezdoForgatas;

        Debug.Log("A gömb visszakerült a kezdő pozícióba.", this);
    }

    private void OnCollisionEnter(Collision utkozes)
    {
        Debug.Log($"A gömb ütközött ezzel: {utkozes.gameObject.name}", this);
    }
}
