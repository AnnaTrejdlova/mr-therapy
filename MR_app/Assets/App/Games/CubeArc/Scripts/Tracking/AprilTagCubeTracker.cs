using System;
using System.Collections.Generic;
using AprilTag;
using CubeArc;
using Meta.XR;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Sleduje fyzickou kostku s AprilTag markery (tagStandard41h12, ID 0–5) v obraze passthrough kamery.
///
/// Postup pro každý nový snímek kamery:
///  1. uloží pózu kamery v čase snímku (GetCameraPose),
///  2. neblokujícím AsyncGPUReadback stáhne obraz z GPU,
///  3. po stažení spustí detektor, převede pózy tagů do světa a z nich spočítá střed kostky,
///  4. výsledek vyhladí One Euro filtrem.
///
/// Používá existující PassthroughCameraAccess ze scény (Meta povoluje jen jednu instanci na kameru).
/// </summary>
public class AprilTagCubeTracker : MonoBehaviour, ICubePoseSource
{
    [Header("Kamera")]
    [Tooltip("Když je prázdné, najde se ve scéně (používá ho i video stream).")]
    [SerializeField] private PassthroughCameraAccess cameraAccess;

    [Header("Kostka a markery")]
    [Tooltip("Délka hrany kostky v metrech.")]
    [SerializeField] private float cubeEdge = 0.05f;
    [Tooltip("Velikost tagu pro odhad pózy [m] = 5/9 šířky celého vytištěného tagu (vnitřní bílý rámeček). " +
             "Hodnotu vypíše Documentation/markers/generate_cube_markers.py; pro kostku 50 mm je 0.025.")]
    [SerializeField] private float tagSize = 0.025f;
    [Tooltip("Nechte zapnuté. Vypněte jen pokud ladicí osy ukazují, že osa Z tagu míří ven z kostky.")]
    [SerializeField] private bool tagZPointsIntoCube = true;

    [Header("Detekce")]
    [Tooltip("Zmenšení obrazu před detekcí (2 = rychlejší, mírně méně přesné).")]
    [Range(1, 4)] [SerializeField] private int quadDecimation = 2;
    [Tooltip("Zpracovat obraz v polovičním rozlišení (rychlejší, menší dosah).")]
    [SerializeField] private bool halfResolution = false;

    [Header("Filtrace")]
    [SerializeField] private float filterMinCutoff = 1.5f;
    [SerializeField] private float filterBeta = 4f;
    [Tooltip("Za jak dlouho bez detekce se kostka považuje za ztracenou [s].")]
    [SerializeField] private float lostTimeout = 0.3f;
    [Tooltip("Skok větší než tato vzdálenost mezi měřeními se zahodí jako chyba [m].")]
    [SerializeField] private float maxJump = 0.10f;
    [Range(0f, 1f)] [SerializeField] private float rotationSmoothing = 0.5f;

    [Header("Ladění")]
    [SerializeField] private bool logStats = true;

    /// <summary>Jedna detekce tagu, převedená do světa (pro ladicí zobrazení).</summary>
    public struct WorldTag
    {
        public int Id;
        public Vector3 Position;
        public Quaternion Rotation;
        public float Squareness;
    }

    // --- ICubePoseSource ---
    public bool IsTracked => hasPose && Time.time - lastSeenTime < lostTimeout;
    public Pose Pose => pose;
    public Vector3 Velocity => positionFilter.Velocity;
    public float LastSeenTime => lastSeenTime;
    public float CubeEdge => cubeEdge;
    public bool IsAvailable => cameraAccess != null && PassthroughCameraAccess.IsSupported;

    // --- Ladicí údaje ---
    public IReadOnlyList<WorldTag> LastTags => lastTags;
    public float DetectionsPerSecond { get; private set; }
    public float ProcessedFramesPerSecond { get; private set; }
    public float LastProcessMilliseconds { get; private set; }

    private TagDetector detector;
    private Vector2Int detectorSize;
    private RenderTexture halfResTarget;
    private bool readbackPending;
    private Pose pendingCameraPose;
    private double pendingFrameTime;
    private Vector2Int pendingSize;

    private readonly OneEuroFilter3 positionFilter = new OneEuroFilter3();
    private Pose pose = Pose.identity;
    private bool hasPose;
    private float lastSeenTime = -1000f;
    private int rejectedInRow;
    private readonly List<WorldTag> lastTags = new List<WorldTag>();

    private int statFrames, statDetections;
    private float statStart;

    private void Awake()
    {
        if (cameraAccess == null)
            cameraAccess = FindFirstObjectByType<PassthroughCameraAccess>(FindObjectsInactive.Exclude);

        positionFilter.MinCutoff = filterMinCutoff;
        positionFilter.Beta = filterBeta;
        statStart = Time.realtimeSinceStartup;
    }

    private void OnDestroy()
    {
        detector?.Dispose();
        detector = null;
        if (halfResTarget != null)
        {
            halfResTarget.Release();
            Destroy(halfResTarget);
        }
    }

    private void Update()
    {
        UpdateStats();

        if (cameraAccess == null || !cameraAccess.enabled || !cameraAccess.IsPlaying) return;
        if (readbackPending || !cameraAccess.IsUpdatedThisFrame) return;

        Texture source = cameraAccess.GetTexture();
        if (source == null) return;

        // Póza kamery v čase pořízení snímku (ne aktuální póza hlavy).
        pendingCameraPose = cameraAccess.GetCameraPose();
        pendingFrameTime = Time.realtimeSinceStartupAsDouble;

        Texture readSource = source;
        if (halfResolution)
        {
            int w = source.width / 2, h = source.height / 2;
            if (halfResTarget == null || halfResTarget.width != w || halfResTarget.height != h)
            {
                if (halfResTarget != null) { halfResTarget.Release(); Destroy(halfResTarget); }
                halfResTarget = new RenderTexture(w, h, 0, RenderTextureFormat.ARGB32);
            }
            Graphics.Blit(source, halfResTarget);
            readSource = halfResTarget;
        }

        pendingSize = new Vector2Int(readSource.width, readSource.height);
        readbackPending = true;
        AsyncGPUReadback.Request(readSource, 0, TextureFormat.RGBA32, OnReadback);
    }

    private void OnReadback(AsyncGPUReadbackRequest request)
    {
        readbackPending = false;
        if (this == null || request.hasError) return;

        float start = Time.realtimeSinceStartup;
        NativeArray<Color32> pixels = request.GetData<Color32>();
        ProcessFrame(pixels, pendingSize, pendingCameraPose, pendingFrameTime);
        LastProcessMilliseconds = (Time.realtimeSinceStartup - start) * 1000f;
        statFrames++;
    }

    private void ProcessFrame(NativeArray<Color32> pixels, Vector2Int size, Pose cameraPose, double frameTime)
    {
        if (detector == null || detectorSize != size)
        {
            detector?.Dispose();
            detector = new TagDetector(size.x, size.y, quadDecimation);
            detectorSize = size;
        }

        ComputeCameraModel(size, out float fovRadians, out Vector2 principalCorrection);
        detector.ProcessImage(pixels.AsReadOnlySpan(), fovRadians, tagSize);

        lastTags.Clear();
        float halfEdge = cubeEdge * 0.5f;
        Vector3 weightedCenter = Vector3.zero;
        float totalWeight = 0f;
        Quaternion bestRotation = Quaternion.identity;
        float bestSquareness = -1f;

        foreach (TagPose tag in detector.DetectedTags)
        {
            if (!CubeFaceLayout.IsKnownTag(tag.ID)) continue;

            // Detektor předpokládá optický střed uprostřed obrazu; opravíme na skutečný.
            Vector3 camPos = tag.Position;
            camPos.x += camPos.z * principalCorrection.x;
            camPos.y += camPos.z * principalCorrection.y;

            Vector3 worldPos = cameraPose.position + cameraPose.rotation * camPos;
            Quaternion worldRot = cameraPose.rotation * tag.Rotation;

            // Jak moc tag míří ke kameře (1 = kolmo). Šikmé tagy mají horší odhad natočení.
            Vector3 outward = worldRot * (tagZPointsIntoCube ? Vector3.back : Vector3.forward);
            float squareness = Vector3.Dot(outward, (cameraPose.position - worldPos).normalized);
            if (squareness <= 0.1f) continue; // tag "zezadu" = chybná detekce

            lastTags.Add(new WorldTag { Id = tag.ID, Position = worldPos, Rotation = worldRot, Squareness = squareness });

            Pose cube = CubeFaceLayout.CubePoseFromTag(tag.ID, worldPos, worldRot, halfEdge, tagZPointsIntoCube);
            float weight = squareness * squareness;
            weightedCenter += cube.position * weight;
            totalWeight += weight;
            if (squareness > bestSquareness)
            {
                bestSquareness = squareness;
                bestRotation = cube.rotation;
            }
        }

        if (totalWeight <= 0f) return;

        Vector3 measured = weightedCenter / totalWeight;
        AcceptMeasurement(measured, bestRotation, frameTime);
        statDetections++;
    }

    private void AcceptMeasurement(Vector3 position, Quaternion rotation, double frameTime)
    {
        bool recentlyTracked = IsTracked;
        if (recentlyTracked && Vector3.Distance(position, positionFilter.Value) > maxJump)
        {
            // Ojedinělý skok je skoro jistě chybná detekce. Několik po sobě znamená, že se kostka opravdu přesunula.
            rejectedInRow++;
            if (rejectedInRow < 3) return;
        }
        rejectedInRow = 0;

        if (!recentlyTracked) positionFilter.Reset();
        Vector3 filtered = positionFilter.Filter(position, frameTime);
        Quaternion filteredRotation = recentlyTracked
            ? Quaternion.Slerp(rotation, pose.rotation, rotationSmoothing)
            : rotation;

        pose = new Pose(filtered, filteredRotation);
        hasPose = true;
        lastSeenTime = Time.time;
    }

    /// <summary>
    /// Zorné pole a oprava optického středu pro zpracovávané rozlišení.
    /// Obraz kamery je výřez senzoru se stejným středem (viz PassthroughCameraAccess.CalcSensorCropRegion).
    /// </summary>
    private void ComputeCameraModel(Vector2Int size, out float fovRadians, out Vector2 principalCorrection)
    {
        var intr = cameraAccess.Intrinsics;
        Vector2 sensor = intr.SensorResolution;
        Vector2 current = cameraAccess.CurrentResolution;

        Vector2 scale = current / sensor;
        scale /= Mathf.Max(scale.x, scale.y);
        float cropHeight = sensor.y * scale.y;

        // Pixely zpracovávaného obrazu na pixel senzoru.
        float pixelsPerSensorPixel = size.y / cropHeight;
        float focalY = intr.FocalLength.y * pixelsPerSensorPixel;
        fovRadians = 2f * Mathf.Atan(size.y * 0.5f / focalY);

        Vector2 cropCenter = sensor * 0.5f;
        principalCorrection = new Vector2(
            (cropCenter.x - intr.PrincipalPoint.x) / intr.FocalLength.x,
            (cropCenter.y - intr.PrincipalPoint.y) / intr.FocalLength.y);
    }

    private void UpdateStats()
    {
        float elapsed = Time.realtimeSinceStartup - statStart;
        if (elapsed < 2f) return;

        ProcessedFramesPerSecond = statFrames / elapsed;
        DetectionsPerSecond = statDetections / elapsed;
        if (logStats)
        {
            Debug.Log($"[CubeTracker] frames {ProcessedFramesPerSecond:F1}/s, detections {DetectionsPerSecond:F1}/s, " +
                      $"process {LastProcessMilliseconds:F1} ms, tags {lastTags.Count}, tracked {IsTracked}");
        }
        statFrames = 0;
        statDetections = 0;
        statStart = Time.realtimeSinceStartup;
    }
}
