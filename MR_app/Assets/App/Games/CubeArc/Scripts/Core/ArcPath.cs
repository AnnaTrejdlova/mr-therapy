using UnityEngine;

namespace CubeArc
{
    /// <summary>Výsledek promítnutí bodu na oblouk.</summary>
    public struct ArcProjection
    {
        /// <summary>Poloha na oblouku 0 (start) až 1 (cíl).</summary>
        public float T;
        /// <summary>Nejbližší bod oblouku.</summary>
        public Vector3 Closest;
        /// <summary>Odchylka v rovině oblouku se znaménkem [m]: + ven (nad oblouk), − dovnitř (pod oblouk).</summary>
        public float RadialDeviation;
        /// <summary>Odchylka kolmo na rovinu oblouku [m]: + od pacienta, − k pacientovi.</summary>
        public float Depth;
        /// <summary>Výška nad základnou oblouku [m] = o kolik je kostka zvednutá oproti poloze na stole.</summary>
        public float Height;
        /// <summary>Bod leží mimo rozsah oblouku (pod základnou za startem nebo za cílem).</summary>
        public bool OutsideRange;
        /// <summary>Celková vzdálenost od oblouku [m] (koridor je trubice kolem oblouku).</summary>
        public float Deviation;
    }

    /// <summary>
    /// Svislý půlkruh ("duha") stojící na stole před pacientem: začíná na stole na jedné straně,
    /// vede nahoru přes vrchol a končí na stole na druhé straně. Rovina oblouku je kolmá na stůl
    /// a natočená čelem k pacientovi.
    ///
    /// Souřadnice: Right = vodorovně doprava, Up = svisle nahoru, Forward = normála roviny (od pacienta).
    /// Center leží na základně oblouku ve výšce středu kostky ležící na stole.
    /// Bod v čase t: Center + Radius * (s·cos(πt)·Right + sin(πt)·Up), kde s = −1 při startu vlevo.
    /// </summary>
    public readonly struct ArcPath
    {
        public readonly Vector3 Center;
        public readonly Vector3 Right;
        public readonly Vector3 Up;
        public readonly Vector3 Forward;
        public readonly float Radius;
        public readonly bool StartLeft;

        public ArcPath(Vector3 center, Vector3 forward, float radius, bool startLeft)
        {
            Center = center;
            Vector3 flat = new Vector3(forward.x, 0f, forward.z);
            Forward = flat.sqrMagnitude > 1e-6f ? flat.normalized : Vector3.forward;
            Up = Vector3.up;
            Right = Vector3.Cross(Vector3.up, Forward).normalized;
            Radius = radius;
            StartLeft = startLeft;
        }

        private float SideSign => StartLeft ? -1f : 1f;

        public float Length => Mathf.PI * Radius;

        public Vector3 Start => PointAt(0f);
        public Vector3 End => PointAt(1f);
        public Vector3 Top => PointAt(0.5f);

        public Vector3 PointAt(float t)
        {
            float phi = Mathf.PI * Mathf.Clamp01(t);
            return Center + Radius * (SideSign * Mathf.Cos(phi) * Right + Mathf.Sin(phi) * Up);
        }

        /// <summary>Jednotkový směr pohybu po oblouku v bodě t.</summary>
        public Vector3 TangentAt(float t)
        {
            float phi = Mathf.PI * Mathf.Clamp01(t);
            return (-SideSign * Mathf.Sin(phi) * Right + Mathf.Cos(phi) * Up).normalized;
        }

        /// <summary>Vnější normála oblouku v jeho rovině (od středu ven) v bodě t.</summary>
        public Vector3 OutwardAt(float t)
        {
            float phi = Mathf.PI * Mathf.Clamp01(t);
            return (SideSign * Mathf.Cos(phi) * Right + Mathf.Sin(phi) * Up).normalized;
        }

        /// <summary>Převod světového bodu do souřadnic oblouku (x doprava, y nahoru, z od pacienta).</summary>
        public Vector3 ToLocal(Vector3 world)
        {
            Vector3 d = world - Center;
            return new Vector3(Vector3.Dot(d, Right), Vector3.Dot(d, Up), Vector3.Dot(d, Forward));
        }

        public ArcProjection Project(Vector3 world)
        {
            Vector3 local = ToLocal(world);
            float x = local.x, y = local.y, depth = local.z;
            float rho = Mathf.Sqrt(x * x + y * y);
            var result = new ArcProjection { Height = y, Depth = depth };

            // Úhel měřený od startu; nad základnou je 0..π.
            float phi = Mathf.Atan2(y, SideSign * x);
            if (phi >= 0f && rho > 1e-6f)
            {
                result.T = phi / Mathf.PI;
                result.Closest = PointAt(result.T);
                result.RadialDeviation = rho - Radius;
                result.OutsideRange = false;
            }
            else
            {
                // Pod základnou (nebo přesně ve středu): nejbližší je krajní bod.
                Vector3 start = Start, end = End;
                bool nearStart = Vector3.Distance(world, start) <= Vector3.Distance(world, end);
                result.T = nearStart ? 0f : 1f;
                result.Closest = nearStart ? start : end;
                Vector3 inPlane = ToLocal(result.Closest);
                result.RadialDeviation = new Vector2(x - inPlane.x, y - inPlane.y).magnitude;
                result.OutsideRange = true;
            }

            result.Deviation = Mathf.Sqrt(result.RadialDeviation * result.RadialDeviation + depth * depth);
            return result;
        }
    }
}
