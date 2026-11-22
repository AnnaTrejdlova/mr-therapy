using UnityEngine;

/// <summary>
/// Zdroj pózy fyzické kostky. Hra pracuje jen s tímto rozhraním, takže lze vyměnit
/// detekci markerů (AprilTag, OpenCV) nebo použít ovladač místo kostky pro testování.
/// </summary>
public interface ICubePoseSource
{
    /// <summary>True, pokud byla kostka viděna nedávno (v rámci timeoutu zdroje).</summary>
    bool IsTracked { get; }

    /// <summary>Póza středu kostky ve světových souřadnicích (poslední známá).</summary>
    Pose Pose { get; }

    /// <summary>Vyhlazená rychlost středu kostky [m/s].</summary>
    Vector3 Velocity { get; }

    /// <summary>Time.time posledního úspěšného měření.</summary>
    float LastSeenTime { get; }

    /// <summary>Délka hrany kostky [m].</summary>
    float CubeEdge { get; }

    /// <summary>Zda zdroj může na tomto zařízení vůbec fungovat.</summary>
    bool IsAvailable { get; }

    /// <summary>Zdroj sleduje skutečnou kostku (natočení odpovídá ležící kostce). Ovladač místo kostky = false.</summary>
    bool IsPhysicalCube { get; }

    /// <summary>Póza je právě jen odhadnutá (např. z pohybu ruky při zakrytí kostky), ne naměřená.</summary>
    bool IsEstimated { get; }
}
