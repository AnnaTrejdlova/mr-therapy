using System.Collections.Generic;
using TMPro;
using UnityEngine;

/// <summary>
/// Ladicí zobrazení sledování kostky: osy každého detekovaného tagu (X červená, Y zelená, Z modrá),
/// obrys odhadnuté kostky a text s frekvencí detekce.
/// Slouží k ověření na brýlích: Z musí mířit do kostky a obrys musí sedět na skutečné kostce.
/// </summary>
public class CubeTrackerDebugOverlay : MonoBehaviour
{
    [SerializeField] private AprilTagCubeTracker tracker;
    [SerializeField] private Material lineMaterial;
    [SerializeField] private float axisLength = 0.04f;

    private readonly List<LineRenderer[]> axisPool = new List<LineRenderer[]>();
    private LineRenderer cubeOutline;
    private TextMeshPro statsText;

    private static readonly Color[] AxisColors = { Color.red, Color.green, Color.blue };

    // Obrys krychle jako jedna lomená čára přes všech 12 hran (některé dvakrát).
    private static readonly Vector3[] OutlinePath =
    {
        new Vector3(-1,-1,-1), new Vector3( 1,-1,-1), new Vector3( 1, 1,-1), new Vector3(-1, 1,-1), new Vector3(-1,-1,-1),
        new Vector3(-1,-1, 1), new Vector3( 1,-1, 1), new Vector3( 1, 1, 1), new Vector3(-1, 1, 1), new Vector3(-1,-1, 1),
        new Vector3(-1, 1, 1), new Vector3(-1, 1,-1), new Vector3( 1, 1,-1), new Vector3( 1, 1, 1), new Vector3( 1,-1, 1), new Vector3( 1,-1,-1)
    };

    private void Awake()
    {
        if (tracker == null) tracker = GetComponentInParent<AprilTagCubeTracker>();

        cubeOutline = CreateLine("CubeOutline", Color.yellow, OutlinePath.Length, 0.002f);

        var textObject = new GameObject("TrackerStats");
        textObject.transform.SetParent(transform, false);
        statsText = textObject.AddComponent<TextMeshPro>();
        statsText.fontSize = 0.25f;
        statsText.alignment = TextAlignmentOptions.Center;
        statsText.rectTransform.sizeDelta = new Vector2(0.4f, 0.1f);
    }

    private void LateUpdate()
    {
        if (tracker == null) return;

        var tags = tracker.LastTags;
        bool fresh = tracker.IsTracked;
        while (axisPool.Count < tags.Count) axisPool.Add(CreateAxes());

        for (int i = 0; i < axisPool.Count; i++)
        {
            bool show = fresh && i < tags.Count;
            for (int a = 0; a < 3; a++) axisPool[i][a].enabled = show;
            if (!show) continue;

            var tag = tags[i];
            Vector3[] dirs = { tag.Rotation * Vector3.right, tag.Rotation * Vector3.up, tag.Rotation * Vector3.forward };
            for (int a = 0; a < 3; a++)
            {
                axisPool[i][a].SetPosition(0, tag.Position);
                axisPool[i][a].SetPosition(1, tag.Position + dirs[a] * axisLength);
            }
        }

        cubeOutline.enabled = fresh;
        if (fresh)
        {
            Pose pose = tracker.Pose;
            float half = tracker.CubeEdge * 0.5f;
            for (int i = 0; i < OutlinePath.Length; i++)
                cubeOutline.SetPosition(i, pose.position + pose.rotation * (OutlinePath[i] * half));
        }

        Transform head = Camera.main != null ? Camera.main.transform : null;
        if (head != null)
        {
            Vector3 anchor = head.position + head.forward * 0.6f + head.up * -0.25f;
            statsText.transform.SetPositionAndRotation(anchor, Quaternion.LookRotation(anchor - head.position, head.up));
        }

        string ids = "";
        foreach (var t in tags) ids += $"{t.Id}({t.Squareness:F2}) ";
        statsText.text = $"kamera {tracker.ProcessedFramesPerSecond:F0}/s  detekce {tracker.DetectionsPerSecond:F0}/s  " +
                         $"{tracker.LastProcessMilliseconds:F0} ms\ntagy: {ids}";
    }

    private LineRenderer[] CreateAxes()
    {
        var axes = new LineRenderer[3];
        for (int a = 0; a < 3; a++) axes[a] = CreateLine("Axis", AxisColors[a], 2, 0.003f);
        return axes;
    }

    private LineRenderer CreateLine(string name, Color color, int points, float width)
    {
        var go = new GameObject(name);
        go.transform.SetParent(transform, false);
        var line = go.AddComponent<LineRenderer>();
        line.useWorldSpace = true;
        line.positionCount = points;
        line.widthMultiplier = width;
        line.sharedMaterial = lineMaterial;
        line.startColor = line.endColor = color;
        line.enabled = false;
        return line;
    }
}
