using UnityEngine;

/// <summary>Procedurálně generované meshe pro hru CubeArc (všechny mají bílé barvy vrcholů pro shader CubeArc/UnlitVertexColor).</summary>
public static class CubeArcMeshes
{
    /// <summary>Krychle o hraně 1 se středem v počátku.</summary>
    public static Mesh Box()
    {
        var mesh = new Mesh { name = "CubeArcBox" };
        Vector3[] n = { Vector3.up, Vector3.down, Vector3.forward, Vector3.back, Vector3.left, Vector3.right };
        var vertices = new Vector3[24];
        var triangles = new int[36];

        for (int f = 0; f < 6; f++)
        {
            Vector3 normal = n[f];
            Vector3 u = Mathf.Abs(normal.y) > 0.5f ? Vector3.right : Vector3.up;
            Vector3 v = Vector3.Cross(normal, u);
            Vector3 c = normal * 0.5f;
            vertices[f * 4 + 0] = c + (-u - v) * 0.5f;
            vertices[f * 4 + 1] = c + (u - v) * 0.5f;
            vertices[f * 4 + 2] = c + (u + v) * 0.5f;
            vertices[f * 4 + 3] = c + (-u + v) * 0.5f;

            int t = f * 6, b = f * 4;
            triangles[t + 0] = b; triangles[t + 1] = b + 1; triangles[t + 2] = b + 2;
            triangles[t + 3] = b; triangles[t + 4] = b + 2; triangles[t + 5] = b + 3;
        }

        mesh.vertices = vertices;
        mesh.colors = White(vertices.Length);
        mesh.triangles = triangles; // shader má Cull Off, na pořadí vrcholů nezáleží
        mesh.RecalculateBounds();
        return mesh;
    }

    /// <summary>Plochý mezikruží v rovině XZ (y = 0).</summary>
    public static Mesh Ring(float innerRadius, float outerRadius, int segments = 48)
    {
        var mesh = new Mesh { name = "CubeArcRing" };
        var vertices = new Vector3[(segments + 1) * 2];
        var triangles = new int[segments * 6];

        for (int i = 0; i <= segments; i++)
        {
            float a = i / (float)segments * Mathf.PI * 2f;
            Vector3 dir = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
            vertices[i * 2] = dir * innerRadius;
            vertices[i * 2 + 1] = dir * outerRadius;
            if (i == segments) break;

            int t = i * 6, b = i * 2;
            triangles[t + 0] = b; triangles[t + 1] = b + 1; triangles[t + 2] = b + 3;
            triangles[t + 3] = b; triangles[t + 4] = b + 3; triangles[t + 5] = b + 2;
        }

        mesh.vertices = vertices;
        mesh.colors = White(vertices.Length);
        mesh.triangles = triangles;
        mesh.RecalculateBounds();
        return mesh;
    }

    /// <summary>Plný kruh v rovině XZ.</summary>
    public static Mesh Disc(float radius, int segments = 48)
    {
        var mesh = new Mesh { name = "CubeArcDisc" };
        var vertices = new Vector3[segments + 1];
        var triangles = new int[segments * 3];
        vertices[0] = Vector3.zero;
        for (int i = 0; i < segments; i++)
        {
            float a = i / (float)segments * Mathf.PI * 2f;
            vertices[i + 1] = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)) * radius;
            triangles[i * 3 + 0] = 0;
            triangles[i * 3 + 1] = i + 1;
            triangles[i * 3 + 2] = (i + 1) % segments + 1;
        }
        mesh.vertices = vertices;
        mesh.colors = White(vertices.Length);
        mesh.triangles = triangles;
        mesh.RecalculateBounds();
        return mesh;
    }

    public static Color[] White(int count)
    {
        var colors = new Color[count];
        for (int i = 0; i < count; i++) colors[i] = Color.white;
        return colors;
    }
}
