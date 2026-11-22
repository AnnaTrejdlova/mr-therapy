using CubeArc;
using UnityEngine;

/// <summary>
/// Obal kolem sledování markerů: když kamera kostku krátce ztratí (typicky ji zakryje ruka, která ji nese),
/// pokračuje kostka s rukou, která ji držela (Quest hand tracking, 60+ Hz), s posledním naměřeným posunem.
/// Jakmile kamera kostku znovu uvidí, platí zase měření z markerů.
///
/// Přemostění se použije jen tehdy, když se kostka a ruka těsně předtím hýbaly spolu (viz HandGrip),
/// a nejdéle MaxBridgeDuration sekund. Čas přemostění se zapisuje do metrik kola (hand_bridged_s).
/// </summary>
public class HandBridgedCubeSource : MonoBehaviour, ICubePoseSource
{
    [SerializeField] private AprilTagCubeTracker markerTracker;
    [Tooltip("Přemosťovat výpadky kamery pohybem ruky.")]
    [SerializeField] private bool bridgeWithHands = true;
    [Tooltip("Nejdelší výpadek kamery, který se ještě přemostí rukou [s].")]
    [SerializeField] private float maxBridgeDuration = 3f;
    [Tooltip("Po jaké době bez nového měření z kamery se přepne na ruku [s].")]
    [SerializeField] private float markerStaleAfter = 0.12f;

    private OVRCameraRig rig;
    private readonly HandGrip leftGrip = new HandGrip();
    private readonly HandGrip rightGrip = new HandGrip();
    private readonly OneEuroFilter3 bridgeVelocity = new OneEuroFilter3(3f, 0f, 3f);

    private float lastMarkerSample = float.NegativeInfinity;
    private Pose pose = Pose.identity;
    private Vector3 velocity;
    private bool tracked;
    private bool estimated;
    private float lastSeenTime = -1000f;

    public bool IsTracked => tracked;
    public Pose Pose => pose;
    public Vector3 Velocity => velocity;
    public float LastSeenTime => lastSeenTime;
    public float CubeEdge => markerTracker != null ? markerTracker.CubeEdge : 0.05f;
    public bool IsAvailable => markerTracker != null && markerTracker.IsAvailable;
    public bool IsPhysicalCube => true;
    public bool IsEstimated => estimated;

    /// <summary>Která ruka kostku drží (pro ladicí zobrazení): "L", "P" nebo "".</summary>
    public string HoldingHand => leftGrip.IsHolding ? "L" : rightGrip.IsHolding ? "P" : "";

    private void Awake()
    {
        rig = FindFirstObjectByType<OVRCameraRig>();
        leftGrip.MaxBridgeDuration = rightGrip.MaxBridgeDuration = maxBridgeDuration;
    }

    private void OnEnable()
    {
        leftGrip.Reset();
        rightGrip.Reset();
        lastMarkerSample = float.NegativeInfinity;
    }

    private void Update()
    {
        if (markerTracker == null) { tracked = false; return; }

        float now = Time.time;
        bool leftTracked = TryGetHand(OVRInput.Controller.LHand, out Pose leftHand);
        bool rightTracked = TryGetHand(OVRInput.Controller.RHand, out Pose rightHand);

        // Nové měření z kamery: aktualizovat, kterou rukou je kostka držená.
        if (markerTracker.LastSeenTime > lastMarkerSample)
        {
            lastMarkerSample = markerTracker.LastSeenTime;
            leftGrip.ObserveCube(now, markerTracker.Pose, leftTracked, leftHand);
            rightGrip.ObserveCube(now, markerTracker.Pose, rightTracked, rightHand);
        }

        bool markerFresh = markerTracker.IsTracked && now - markerTracker.LastSeenTime < markerStaleAfter;
        if (markerFresh)
        {
            UseMarker();
            return;
        }

        if (bridgeWithHands && TryBridge(now, leftTracked, leftHand, rightTracked, rightHand, out Pose bridged))
        {
            if (!estimated) bridgeVelocity.Reset();
            bridgeVelocity.Filter(bridged.position, Time.timeAsDouble);
            pose = bridged;
            velocity = bridgeVelocity.Velocity;
            tracked = true;
            estimated = true;
            lastSeenTime = now;
            return;
        }

        if (markerTracker.IsTracked) { UseMarker(); return; } // krátké podržení poslední pózy (lostTimeout trackeru)

        tracked = false;
        estimated = false;
        velocity = Vector3.zero;
    }

    private void UseMarker()
    {
        pose = markerTracker.Pose;
        velocity = markerTracker.Velocity;
        tracked = true;
        estimated = false;
        lastSeenTime = markerTracker.LastSeenTime;
    }

    private bool TryBridge(float now, bool leftTracked, Pose leftHand, bool rightTracked, Pose rightHand, out Pose cube)
    {
        // Když drží obě ruce, platí ta bližší.
        bool leftFirst = leftGrip.LastDistance <= rightGrip.LastDistance;
        if (leftFirst)
            return leftGrip.TryBridge(now, leftTracked, leftHand, out cube) || rightGrip.TryBridge(now, rightTracked, rightHand, out cube);
        return rightGrip.TryBridge(now, rightTracked, rightHand, out cube) || leftGrip.TryBridge(now, leftTracked, leftHand, out cube);
    }

    private bool TryGetHand(OVRInput.Controller hand, out Pose result)
    {
        result = default;
        if (rig == null || !OVRInput.IsControllerConnected(hand) || !OVRInput.GetControllerPositionTracked(hand)) return false;
        Transform anchor = hand == OVRInput.Controller.LHand ? rig.leftHandAnchor : rig.rightHandAnchor;
        if (anchor == null) return false;
        result = new Pose(anchor.position, anchor.rotation);
        return true;
    }
}
