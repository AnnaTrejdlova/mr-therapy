using CubeArc;
using UnityEngine;

/// <summary>
/// Testovací zdroj pózy: pravý ovladač (nebo pravá ruka) zastupuje fyzickou kostku.
/// Pro Editor, Quest Link a Meta XR Simulator, kde passthrough kamera není k dispozici,
/// a pro vyzkoušení hry bez vytištěné kostky.
/// </summary>
public class ControllerCubePoseSource : MonoBehaviour, ICubePoseSource
{
    [SerializeField] private float cubeEdge = 0.05f;
    [Tooltip("Posun středu virtuální kostky od ovladače, v jeho souřadnicích [m].")]
    [SerializeField] private Vector3 offset = new Vector3(0f, 0f, 0.05f);

    private OVRCameraRig rig;
    private readonly OneEuroFilter3 velocityFilter = new OneEuroFilter3(3f, 0f, 3f);
    private Pose pose = Pose.identity;
    private bool tracked;
    private float lastSeenTime = -1000f;

    public bool IsTracked => tracked;
    public Pose Pose => pose;
    public Vector3 Velocity => velocityFilter.Velocity;
    public float LastSeenTime => lastSeenTime;
    public float CubeEdge => cubeEdge;
    public bool IsAvailable => rig != null;

    private void Awake()
    {
        rig = FindFirstObjectByType<OVRCameraRig>();
    }

    private void Update()
    {
        tracked = false;
        if (rig == null) return;

        Transform anchor = null;
        if (OVRInput.IsControllerConnected(OVRInput.Controller.RTouch))
            anchor = rig.rightControllerAnchor;
        else if (OVRInput.IsControllerConnected(OVRInput.Controller.RHand))
            anchor = rig.rightHandAnchor;

        if (anchor == null) return;

        Vector3 position = anchor.TransformPoint(offset);
        velocityFilter.Filter(position, Time.timeAsDouble);
        pose = new Pose(position, anchor.rotation);
        tracked = true;
        lastSeenTime = Time.time;
    }
}
