using System.Collections;
using CubeArc;
using TMPro;
using UnityEngine;

/// <summary>
/// Průběh hry "Přenášení kostky po oblouku" pro jednu úroveň (všechna kola).
///
/// Kolo: kostka na stole → postaví se svislý oblouk (duha) čelem k pacientovi → kostka do startovního
/// kroužku → zvednout a přenést po oblouku přes vrchol do cíle → kostka v cíli leží v klidu 0,5 s
/// → kolo končí samo (bez tlačítka).
/// Start se každé kolo střídá vlevo / vpravo.
/// </summary>
public class CubeArcLevelManager : MonoBehaviour
{
    private enum Phase { Setup, WaitForStart, Running, Feedback, Finished }

    private const string GameName = "CubeArc";
    private const float StillSpeed = 0.02f;          // m/s
    private const float RestHeight = 0.02f;          // m nad stolem = kostka leží
    private const float SetupStillTime = 1.0f;       // s
    private const float StartStillTime = 0.5f;       // s
    private const float GoalStillTime = 0.5f;        // s
    private const float FinishProgress = 0.97f;
    private const float LostHintDelay = 2.0f;        // s
    private const float MaxTrialDuration = 120f;     // s, pak kolo skončí jako "timeout"
    private const float GhostLead = 0.12f;           // o kolik vodicí kostka předbíhá
    private const float MaxFlatTilt = 20f;           // ° – jak moc smí být kostka nakloněná, aby "ležela"

    private ICubePoseSource source;
    private CubeArcDifficulty settings;
    private int difficulty;
    private bool startLeft;
    private Material material;

    private GuideTrail trail;
    private TextMeshPro taskText;
    private GameObject cubeHighlight;
    private MeshRenderer cubeHighlightRenderer;
    private MaterialPropertyBlock highlightBlock;

    private Phase phase = Phase.Setup;
    private float levelStartTime;
    private float phaseStillTime;
    private bool hasTable;
    private float tableCenterHeight; // výška středu kostky ležící na stole
    private ArcPath arc;
    private TrialRecorder recorder;
    private bool wasInside = true;
    private bool lostLogged;
    private float demoT;

    /// <summary>Spustí úroveň. Volá MainCubeArcManager.</summary>
    public void Begin(ICubePoseSource poseSource, CubeArcDifficulty levelSettings, int level, bool firstStartLeft, int totalIterations, Material visualsMaterial)
    {
        source = poseSource;
        settings = levelSettings;
        difficulty = level;
        startLeft = firstStartLeft;
        material = visualsMaterial;

        if (SessionManager.Instance != null)
        {
            SessionManager.Instance.TotalIterations = totalIterations;
            SessionManager.Instance.CurrentIteration = 1;
        }

        levelStartTime = Time.time;
        CreateVisuals();
        EnterSetup();
        SessionManager.Instance?.SendSystemStatus("active", GameName, difficulty, totalIterations);
    }

    private void CreateVisuals()
    {
        var trailObject = new GameObject("GuideTrail");
        trailObject.transform.SetParent(transform, false);
        trail = trailObject.AddComponent<GuideTrail>();

        var textObject = new GameObject("TaskText");
        textObject.transform.SetParent(transform, false);
        taskText = textObject.AddComponent<TextMeshPro>();
        taskText.fontSize = 0.6f;
        taskText.alignment = TextAlignmentOptions.Center;
        taskText.rectTransform.sizeDelta = new Vector2(0.7f, 0.3f);
        taskText.color = Color.white;
        taskText.outlineWidth = 0.2f;
        taskText.outlineColor = new Color32(0, 0, 0, 200);

        cubeHighlight = new GameObject("CubeHighlight");
        cubeHighlight.transform.SetParent(transform, false);
        cubeHighlight.AddComponent<MeshFilter>().sharedMesh = CubeArcMeshes.Box();
        cubeHighlightRenderer = cubeHighlight.AddComponent<MeshRenderer>();
        cubeHighlightRenderer.sharedMaterial = material;
        cubeHighlightRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        highlightBlock = new MaterialPropertyBlock();
        cubeHighlight.SetActive(false);
    }

    private void OnDestroy()
    {
        if (cubeHighlight != null)
        {
            var filter = cubeHighlight.GetComponent<MeshFilter>();
            if (filter != null && filter.sharedMesh != null) Destroy(filter.sharedMesh);
        }
    }

    private void Update()
    {
        if (source == null || phase == Phase.Finished) return;

        UpdateCubeHighlight();

        switch (phase)
        {
            case Phase.Setup: UpdateSetup(); break;
            case Phase.WaitForStart: UpdateWaitForStart(); break;
            case Phase.Running: UpdateRunning(); break;
        }

        PlaceTaskText();
    }

    // ---------- Fáze 1: kostka na stůl (určí výšku stolu) ----------

    private void EnterSetup()
    {
        phase = Phase.Setup;
        phaseStillTime = 0f;
        SetText("Položte kostku na stůl před sebe.");
    }

    private void UpdateSetup()
    {
        if (!source.IsTracked)
        {
            phaseStillTime = 0f;
            SetText("Položte kostku na stůl před sebe.\n<size=70%>Kostka zatím není vidět – podívejte se na ni.</size>");
            return;
        }

        SetText("Položte kostku na stůl před sebe.\n<size=70%>Nechte ji chvíli ležet.</size>");
        if (!IsStill() || !IsLyingFlat()) { phaseStillTime = 0f; return; }

        phaseStillTime += Time.deltaTime;
        if (phaseStillTime < SetupStillTime) return;

        tableCenterHeight = source.Pose.position.y;
        hasTable = true;
        LogEvent("Setup_Table", $"table_y={tableCenterHeight - source.CubeEdge * 0.5f:F3}");
        BuildArcAndWaitForStart();
    }

    // ---------- Fáze 2: kostka do startovního kroužku ----------

    private void BuildArcAndWaitForStart()
    {
        Transform head = Camera.main != null ? Camera.main.transform : transform;
        Vector3 forward = Vector3.ProjectOnPlane(head.forward, Vector3.up);
        if (forward.sqrMagnitude < 1e-4f) forward = Vector3.ProjectOnPlane(head.up, Vector3.up); // hlava sklopená úplně dolů
        forward.Normalize();

        // Základna oblouku je ve výšce středu ležící kostky, takže start i cíl jsou na stole.
        Vector3 center = new Vector3(head.position.x, tableCenterHeight, head.position.z) + forward * settings.centerDistance;
        arc = new ArcPath(center, forward, settings.radius, startLeft);

        trail.Build(arc, settings.corridorHalfWidth, source.CubeEdge, settings.visibleAhead, material);
        trail.SetStartVisible(true);
        trail.SetGoalVisible(true);

        phase = Phase.WaitForStart;
        phaseStillTime = 0f;
        demoT = 0f;
        SetText($"Kolo {CurrentIteration}/{TotalIterations}\nPřesuňte kostku do <color=#4CF26B>zeleného kruhu</color>.");
    }

    private void UpdateWaitForStart()
    {
        // Vodicí kostka mezitím předvádí celou cestu.
        demoT += Time.deltaTime / 3f;
        if (demoT > 1.3f) demoT = 0f;
        trail.UpdateGhost(settings.showGhost, Mathf.Clamp01(demoT), Time.deltaTime, instant: true);

        if (!source.IsTracked) { phaseStillTime = 0f; return; }

        Vector3 p = source.Pose.position;
        bool inStart = HorizontalDistance(p, arc.Start) <= trail.StartRingRadius;
        if (!inStart || !IsResting(p) || !IsStill()) { phaseStillTime = 0f; return; }

        phaseStillTime += Time.deltaTime;
        if (phaseStillTime >= StartStillTime) StartTrial();
    }

    // ---------- Fáze 3: přenášení ----------

    private void StartTrial()
    {
        phase = Phase.Running;
        phaseStillTime = 0f;
        wasInside = true;
        lostLogged = false;
        recorder = new TrialRecorder(arc, settings.corridorHalfWidth, Time.time);
        trail.SetStartVisible(false);
        trail.UpdateGhost(settings.showGhost, 0f, 0f, instant: true);

        SetText("Zvedněte kostku a přeneste ji po oblouku do <color=#FFD633>cíle</color>.");
        LogEvent("Trial_Start", startLeft ? "left" : "right");
    }

    private void UpdateRunning()
    {
        bool tracked = source.IsTracked;
        Vector3 p = source.Pose.position;
        recorder.Tick(Time.time, tracked, p);

        // Ztráta kostky z dohledu
        float lostFor = Time.time - source.LastSeenTime;
        if (!tracked && lostFor > LostHintDelay)
        {
            SetText("Kostka není vidět – podívejte se na ni.");
            if (!lostLogged) { LogEvent("Cube_Lost", ""); lostLogged = true; }
        }
        else if (tracked && lostLogged)
        {
            lostLogged = false;
            LogEvent("Cube_Found", "");
            SetText("Zvedněte kostku a přeneste ji po oblouku do <color=#FFD633>cíle</color>.");
        }

        var status = GuideTrail.CorridorStatus.Inside;
        if (tracked)
        {
            ArcProjection proj = arc.Project(p);
            status = StatusFor(proj.Deviation);

            bool inside = recorder.IsInsideCorridor;
            if (wasInside && !inside) LogEvent("Corridor_Exit", $"t={proj.T:F2} dev_cm={proj.Deviation * 100f:F1}");
            if (!wasInside && inside) LogEvent("Corridor_Enter", $"t={proj.T:F2}");
            wasInside = inside;
        }

        float progress = recorder.MaxProgress;
        trail.SetProgress(progress, status);
        trail.UpdateGhost(settings.showGhost, Mathf.Min(1f, progress + GhostLead), Time.deltaTime);

        // Konec kola: kostka leží v cíli a je v klidu.
        bool atGoal = tracked && progress >= FinishProgress
                      && HorizontalDistance(p, arc.End) <= trail.GoalRingRadius
                      && IsResting(p) && IsStill();
        phaseStillTime = atGoal ? phaseStillTime + Time.deltaTime : 0f;

        if (phaseStillTime >= GoalStillTime) CompleteTrial("goal");
        else if (recorder.Elapsed > MaxTrialDuration) CompleteTrial("timeout");
    }

    private void CompleteTrial(string reason)
    {
        phase = Phase.Feedback;
        TrialSummary summary = recorder.BuildSummary();
        LogEvent("Trial_Complete", reason, summary);
        trail.UpdateGhost(false, 1f, 0f);
        StartCoroutine(FeedbackThenNext(reason == "goal", summary));
    }

    private IEnumerator FeedbackThenNext(bool reachedGoal, TrialSummary summary)
    {
        if (reachedGoal)
            SetText($"<color=#4CF26B>Výborně!</color>\nČas {summary.duration_s:F1} s\n<size=70%>Čekejte na další kolo...</size>");
        else
            SetText("Čas vypršel.\n<size=70%>Čekejte na další kolo...</size>");

        yield return new WaitForSeconds(3f);

        if (SessionManager.Instance != null && SessionManager.Instance.CurrentIteration < SessionManager.Instance.TotalIterations)
        {
            SessionManager.Instance.NextIteration();
            startLeft = !startLeft; // střídání stran
            BuildArcAndWaitForStart();
        }
        else
        {
            FinishLevel();
        }
    }

    private void FinishLevel()
    {
        phase = Phase.Finished;
        trail.Clear();
        cubeHighlight.SetActive(false);
        SetText("<color=#4CF26B>Skvělá práce!</color>\nÚroveň dokončena.");
    }

    // ---------- Pomocné ----------

    private int CurrentIteration => SessionManager.Instance != null ? SessionManager.Instance.CurrentIteration : 1;
    private int TotalIterations => SessionManager.Instance != null ? SessionManager.Instance.TotalIterations : 1;

    private bool IsStill() => source.Velocity.magnitude < StillSpeed;

    private bool IsResting(Vector3 p) => !hasTable || p.y - tableCenterHeight < RestHeight;

    /// <summary>Kostka leží na některé stěně (ne v ruce nakřivo). Ovladač místo kostky se nekontroluje.</summary>
    private bool IsLyingFlat()
    {
        if (!(source is AprilTagCubeTracker)) return true;
        Quaternion r = source.Pose.rotation;
        float best = 0f;
        Vector3[] axes = { Vector3.up, Vector3.right, Vector3.forward };
        foreach (Vector3 a in axes) best = Mathf.Max(best, Mathf.Abs(Vector3.Dot(r * a, Vector3.up)));
        return best > Mathf.Cos(MaxFlatTilt * Mathf.Deg2Rad);
    }

    private GuideTrail.CorridorStatus StatusFor(float deviation)
    {
        float w = settings.corridorHalfWidth;
        if (deviation <= w * 0.7f) return GuideTrail.CorridorStatus.Inside;
        if (deviation <= w) return GuideTrail.CorridorStatus.Edge;
        return GuideTrail.CorridorStatus.Outside;
    }

    private static float HorizontalDistance(Vector3 a, Vector3 b)
    {
        a.y = 0f; b.y = 0f;
        return Vector3.Distance(a, b);
    }

    private void UpdateCubeHighlight()
    {
        bool show = source.IsTracked && phase != Phase.Finished;
        cubeHighlight.SetActive(show);
        if (!show) return;

        Pose pose = source.Pose;
        cubeHighlight.transform.SetPositionAndRotation(pose.position, pose.rotation);
        cubeHighlight.transform.localScale = Vector3.one * source.CubeEdge * 1.08f;

        Color c = Color.white;
        c.a = 0.2f;
        if (phase == Phase.Running) { c = GuideTrail.ColorFor(StatusFor(arc.Project(pose.position).Deviation)); c.a = 0.3f; }
        highlightBlock.SetColor("_Color", c);
        cubeHighlightRenderer.SetPropertyBlock(highlightBlock);
    }

    private void PlaceTaskText()
    {
        Transform head = Camera.main != null ? Camera.main.transform : null;
        if (head == null) return;

        Vector3 target;
        if (phase == Phase.Setup || !hasTable)
        {
            Vector3 fwd = Vector3.ProjectOnPlane(head.forward, Vector3.up).normalized;
            target = head.position + fwd * 0.6f + Vector3.down * 0.15f;
        }
        else
        {
            // Nad vrcholem oblouku a kousek za ním, aby text nezakrýval stopu.
            target = arc.Top + arc.Forward * 0.03f + Vector3.up * 0.19f;
        }

        Transform t = taskText.transform;
        t.position = Vector3.Distance(t.position, target) > 1f
            ? target // první snímek nebo nový oblouk: rovnou na místo
            : Vector3.Lerp(t.position, target, Time.deltaTime * 5f);
        t.rotation = Quaternion.LookRotation(t.position - head.position, Vector3.up);
    }

    private void SetText(string text)
    {
        if (taskText != null && taskText.text != text) taskText.text = text;
    }

    private void LogEvent(string eventType, string details, TrialSummary summary = null)
    {
        if (SessionManager.Instance == null)
        {
            Debug.Log($"[CubeArc] {eventType} {details}");
            return;
        }

        SessionManager.Instance.SendLog(new CubeArcEventData
        {
            event_type = eventType,
            details = details,
            iteration = SessionManager.Instance.CurrentIteration,
            time_since_start = Time.time - levelStartTime,
            difficulty = difficulty,
            start_side = startLeft ? "left" : "right",
            summary = summary
        });
    }
}
