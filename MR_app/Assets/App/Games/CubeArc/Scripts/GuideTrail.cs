using CubeArc;
using UnityEngine;

/// <summary>
/// Vodicí stopa: svislý pás ("duha") stojící na stole čelem k pacientovi podél oblouku
/// (šířka = koridor), šipky ve směru pohybu, startovní a cílový kroužek na stole
/// a poloprůhledná "vodicí" kostka.
///
/// Barvy: hotová část je modrá; zbývající část a šipky mají barvu podle toho, jak je kostka
/// v koridoru (zelená uvnitř, oranžová u okraje, červená mimo).
/// </summary>
public class GuideTrail : MonoBehaviour
{
    public enum CorridorStatus { Inside, Edge, Outside }

    private const int Segments = 96;
    private const float LiftAboveTable = 0.003f;   // kroužky na stole, aby neprobliknuly se stolem
    private const float ChevronsInFront = 0.003f;  // šipky kousek před pásem (blíž k pacientovi)
    private const float ChevronSpacing = 0.06f;

    private static readonly Color DoneColor = new Color(0.25f, 0.75f, 1f, 0.55f);
    private static readonly Color InsideColor = new Color(0.3f, 0.95f, 0.45f, 0.35f);
    private static readonly Color EdgeColor = new Color(1f, 0.65f, 0.1f, 0.45f);
    private static readonly Color OutsideColor = new Color(1f, 0.25f, 0.2f, 0.5f);
    private static readonly Color ChevronColor = new Color(1f, 1f, 1f, 0.85f);
    private static readonly Color StartColor = new Color(0.3f, 0.95f, 0.45f, 0.9f);
    private static readonly Color GoalColor = new Color(1f, 0.85f, 0.2f, 0.9f);
    private static readonly Color GhostColor = new Color(0.6f, 0.9f, 1f, 0.3f);

    private ArcPath arc;
    private float visibleAhead = 1f;
    private Material material;
    private readonly System.Collections.Generic.List<Mesh> ownedMeshes = new System.Collections.Generic.List<Mesh>();

    private Mesh ribbonMesh;
    private Color[] ribbonColors;
    private float[] ribbonT;

    private Mesh chevronMesh;
    private Color[] chevronColors;
    private float[] chevronT;

    private Transform startRing;
    private Transform goalRing;
    private Transform ghost;
    private MeshRenderer ghostRenderer;
    private float ghostT;
    private float cubeHalfEdge;

    public float StartRingRadius { get; private set; }
    public float GoalRingRadius { get; private set; }

    public static Color ColorFor(CorridorStatus status)
    {
        switch (status)
        {
            case CorridorStatus.Edge: return EdgeColor;
            case CorridorStatus.Outside: return OutsideColor;
            default: return InsideColor;
        }
    }

    /// <summary>Postaví stopu pro daný oblouk. Lze volat opakovaně (každé kolo nový oblouk).</summary>
    public void Build(ArcPath arcPath, float corridorHalfWidth, float cubeEdge, float visibleAheadFraction, Material mat)
    {
        Clear();
        arc = arcPath;
        visibleAhead = visibleAheadFraction;
        material = mat;
        cubeHalfEdge = cubeEdge * 0.5f;

        BuildRibbon(corridorHalfWidth);
        BuildChevrons(Mathf.Min(corridorHalfWidth * 0.8f, 0.03f));

        // Kroužky leží na stole pod koncovými body oblouku (oblouk vede středem kostky).
        StartRingRadius = cubeEdge * 0.9f;
        GoalRingRadius = cubeEdge * 0.9f;
        Vector3 toTable = Vector3.down * cubeHalfEdge;
        startRing = CreateRing("StartRing", arc.Start + toTable, StartRingRadius, StartColor);
        goalRing = CreateRing("GoalRing", arc.End + toTable, GoalRingRadius, GoalColor);
        CreateChild("GoalFill", CubeArcMeshes.Disc(GoalRingRadius * 0.95f), new Color(GoalColor.r, GoalColor.g, GoalColor.b, 0.15f))
            .transform.SetParent(goalRing, false);

        var ghostObject = CreateChild("GhostCube", CubeArcMeshes.Box(), GhostColor);
        ghost = ghostObject.transform;
        ghost.localScale = Vector3.one * cubeEdge;
        ghostRenderer = ghostObject.GetComponent<MeshRenderer>();
        ghostRenderer.enabled = false;
        ghostT = 0f;

        SetProgress(0f, CorridorStatus.Inside);
    }

    public void Clear()
    {
        for (int i = transform.childCount - 1; i >= 0; i--) Destroy(transform.GetChild(i).gameObject);
        foreach (Mesh m in ownedMeshes) if (m != null) Destroy(m);
        ownedMeshes.Clear();
        ribbonMesh = chevronMesh = null;
        ghost = null;
        startRing = goalRing = null;
    }

    private void OnDestroy() => Clear();

    public void SetStartVisible(bool visible) { if (startRing != null) startRing.gameObject.SetActive(visible); }
    public void SetGoalVisible(bool visible) { if (goalRing != null) goalRing.gameObject.SetActive(visible); }

    /// <summary>Aktualizuje barvy stopy podle postupu (0..1) a stavu v koridoru.</summary>
    public void SetProgress(float progress, CorridorStatus status)
    {
        if (ribbonMesh == null) return;

        Color remaining = ColorFor(status);
        for (int i = 0; i < ribbonColors.Length; i++)
            ribbonColors[i] = ribbonT[i] <= progress ? DoneColor : Fade(remaining, ribbonT[i], progress);
        ribbonMesh.colors = ribbonColors;

        for (int i = 0; i < chevronColors.Length; i++)
            chevronColors[i] = chevronT[i] <= progress ? Color.clear : Fade(ChevronColor, chevronT[i], progress);
        chevronMesh.colors = chevronColors;
    }

    /// <summary>Vodicí kostka: předvádí cestu (demo) nebo jede kousek před pacientem.</summary>
    public void UpdateGhost(bool visible, float targetT, float deltaTime, bool instant = false)
    {
        if (ghost == null) return;
        ghostRenderer.enabled = visible;
        if (!visible) return;

        ghostT = instant ? targetT : Mathf.MoveTowards(ghostT, targetT, deltaTime * 0.6f);
        // Oblouk vede středem kostky, vodicí kostka jede přímo po něm.
        ghost.SetPositionAndRotation(arc.PointAt(ghostT), Quaternion.LookRotation(arc.Forward, Vector3.up));
    }

    // Část stopy daleko před pacientem se na vyšších úrovních skryje (s plynulým přechodem).
    private Color Fade(Color c, float t, float progress)
    {
        if (visibleAhead >= 0.999f) return c;
        float ahead = t - progress;
        float fadeWidth = 0.08f;
        float alpha = Mathf.Clamp01((visibleAhead - ahead) / fadeWidth);
        c.a *= alpha;
        return c;
    }

    private void BuildRibbon(float halfWidth)
    {
        int count = (Segments + 1) * 2;
        var vertices = new Vector3[count];
        ribbonT = new float[count];
        ribbonColors = new Color[count];
        var triangles = new int[Segments * 6];

        for (int i = 0; i <= Segments; i++)
        {
            float t = i / (float)Segments;
            Vector3 p = arc.PointAt(t);
            Vector3 o = arc.OutwardAt(t); // v rovině oblouku, takže pás stojí svisle
            vertices[i * 2] = transform.InverseTransformPoint(p - o * halfWidth);
            vertices[i * 2 + 1] = transform.InverseTransformPoint(p + o * halfWidth);
            ribbonT[i * 2] = ribbonT[i * 2 + 1] = t;
            if (i == Segments) break;

            int k = i * 6, b = i * 2;
            triangles[k + 0] = b; triangles[k + 1] = b + 1; triangles[k + 2] = b + 3;
            triangles[k + 3] = b; triangles[k + 4] = b + 3; triangles[k + 5] = b + 2;
        }

        ribbonMesh = new Mesh { name = "GuideRibbon" };
        ribbonMesh.vertices = vertices;
        ribbonMesh.colors = ribbonColors;
        ribbonMesh.triangles = triangles;
        ribbonMesh.RecalculateBounds();
        CreateChild("Ribbon", ribbonMesh, Color.white);
    }

    private void BuildChevrons(float size)
    {
        int count = Mathf.Max(2, Mathf.FloorToInt(arc.Length / ChevronSpacing));
        const int VertsPerChevron = 8; // dvě ramena, každé čtyřúhelník
        var vertices = new Vector3[count * VertsPerChevron];
        chevronT = new float[vertices.Length];
        chevronColors = new Color[vertices.Length];
        var triangles = new int[count * 12];

        for (int c = 0; c < count; c++)
        {
            float t = (c + 0.5f) / count;
            Vector3 p = arc.PointAt(t) - arc.Forward * ChevronsInFront;
            Vector3 fwd = arc.TangentAt(t);
            Vector3 side = arc.OutwardAt(t);
            Vector3 back = -fwd * (size * 0.35f); // tloušťka ramene

            // Šipka ">" ve směru pohybu: dvě ramena od zadních rohů ke špičce.
            Vector3 tip = p + fwd * size * 0.5f;
            Vector3[] corners = { p - fwd * size * 0.5f + side * size * 0.6f, p - fwd * size * 0.5f - side * size * 0.6f };

            for (int arm = 0; arm < 2; arm++)
            {
                int b = c * VertsPerChevron + arm * 4;
                vertices[b + 0] = transform.InverseTransformPoint(corners[arm]);
                vertices[b + 1] = transform.InverseTransformPoint(tip);
                vertices[b + 2] = transform.InverseTransformPoint(tip + back);
                vertices[b + 3] = transform.InverseTransformPoint(corners[arm] + back);

                int k = c * 12 + arm * 6;
                triangles[k + 0] = b; triangles[k + 1] = b + 1; triangles[k + 2] = b + 2;
                triangles[k + 3] = b; triangles[k + 4] = b + 2; triangles[k + 5] = b + 3;
            }
            for (int v = 0; v < VertsPerChevron; v++) chevronT[c * VertsPerChevron + v] = t;
        }

        chevronMesh = new Mesh { name = "GuideChevrons" };
        chevronMesh.vertices = vertices;
        chevronMesh.colors = chevronColors;
        chevronMesh.triangles = triangles;
        chevronMesh.RecalculateBounds();
        CreateChild("Chevrons", chevronMesh, Color.white);
    }

    private Transform CreateRing(string name, Vector3 center, float radius, Color color)
    {
        var go = CreateChild(name, CubeArcMeshes.Ring(radius, radius + 0.008f), color);
        go.transform.position = center + Vector3.up * LiftAboveTable;
        return go.transform;
    }

    private GameObject CreateChild(string name, Mesh mesh, Color tint)
    {
        ownedMeshes.Add(mesh);
        var go = new GameObject(name);
        go.transform.SetParent(transform, false);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        var renderer = go.AddComponent<MeshRenderer>();
        renderer.sharedMaterial = material;
        renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        renderer.receiveShadows = false;
        if (tint != Color.white)
        {
            var block = new MaterialPropertyBlock();
            block.SetColor("_Color", tint);
            renderer.SetPropertyBlock(block);
        }
        return go;
    }
}
