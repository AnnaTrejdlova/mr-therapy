using UnityEngine;

namespace CubeArc
{
    /// <summary>
    /// Rozmístění AprilTag markerů (rodina tagStandard41h12, ID 0–5) na fyzické kostce.
    ///
    /// Souřadnice kostky: +Y nahoru (stěna s ID 0), -Z dopředu (stěna s ID 2).
    /// Lepení (kostka stojí stěnou 0 nahoru, díváme se na stěnu 2):
    ///   ID 0 – horní stěna,  horní hrana tagu směřuje ke stěně 3 (od nás)
    ///   ID 1 – spodní stěna, horní hrana tagu směřuje ke stěně 3
    ///   ID 2 – přední stěna, horní hrana tagu nahoru
    ///   ID 3 – zadní stěna,  horní hrana tagu nahoru
    ///   ID 4 – levá stěna,   horní hrana tagu nahoru
    ///   ID 5 – pravá stěna,  horní hrana tagu nahoru
    ///
    /// Souřadnice tagu (po převodu z AprilTag do Unity): +X doprava, +Y k horní hraně tagu,
    /// +Z do tagu, tedy dovnitř kostky.
    /// </summary>
    public static class CubeFaceLayout
    {
        public const int FaceCount = 6;

        // Vnější normála stěny a směr horní hrany tagu, v souřadnicích kostky.
        private static readonly Vector3[] Normals =
        {
            Vector3.up, Vector3.down, Vector3.back, Vector3.forward, Vector3.left, Vector3.right
        };

        private static readonly Vector3[] TagUp =
        {
            Vector3.forward, Vector3.forward, Vector3.up, Vector3.up, Vector3.up, Vector3.up
        };

        private static readonly Quaternion[] TagInCube = BuildTagRotations();

        private static Quaternion[] BuildTagRotations()
        {
            var result = new Quaternion[FaceCount];
            for (int i = 0; i < FaceCount; i++)
            {
                // Osa Z tagu míří dovnitř kostky (proti vnější normále), osa Y k horní hraně.
                result[i] = Quaternion.LookRotation(-Normals[i], TagUp[i]);
            }
            return result;
        }

        public static bool IsKnownTag(int id) => id >= 0 && id < FaceCount;

        /// <summary>Natočení tagu vůči kostce.</summary>
        public static Quaternion TagRotationInCube(int id) => TagInCube[id];

        /// <summary>Vnější normála stěny s daným tagem, v souřadnicích kostky.</summary>
        public static Vector3 FaceNormal(int id) => Normals[id];

        /// <summary>
        /// Z pózy tagu ve světě spočítá pózu středu kostky.
        /// </summary>
        /// <param name="halfEdge">Polovina hrany kostky v metrech.</param>
        /// <param name="tagZPointsIntoCube">Nastavení pro případ, že by převod os z detektoru dával opačnou normálu.</param>
        public static Pose CubePoseFromTag(int id, Vector3 tagPosition, Quaternion tagRotation, float halfEdge, bool tagZPointsIntoCube = true)
        {
            Quaternion rot = tagZPointsIntoCube
                ? tagRotation
                : tagRotation * Quaternion.AngleAxis(180f, Vector3.up);

            Vector3 center = tagPosition + rot * (Vector3.forward * halfEdge);
            Quaternion cubeRotation = rot * Quaternion.Inverse(TagInCube[id]);
            return new Pose(center, cubeRotation);
        }
    }
}
