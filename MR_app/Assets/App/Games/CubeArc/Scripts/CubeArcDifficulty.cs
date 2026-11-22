using UnityEngine;

/// <summary>Parametry jedné úrovně hry "Přenášení kostky po oblouku".</summary>
[System.Serializable]
public class CubeArcDifficulty
{
    [Tooltip("Poloměr svislého půlkruhu [m] = výška vrcholu oblouku nad polohou kostky na stole; start a cíl jsou 2× poloměr od sebe.")]
    public float radius = 0.20f;

    [Tooltip("Vodorovná vzdálenost roviny oblouku před hlavou pacienta [m].")]
    public float centerDistance = 0.30f;

    [Tooltip("Poloměr koridoru (trubice) kolem oblouku [m]. Dál od oblouku je pohyb 'mimo stopu'.")]
    public float corridorHalfWidth = 0.06f;

    [Tooltip("Ukazovat poloprůhlednou kostku, která jede kousek před pacientem.")]
    public bool showGhost = true;

    [Tooltip("Jakou část oblouku před pacientem ukazovat (1 = celou stopu).")]
    [Range(0.1f, 1f)] public float visibleAhead = 1f;

    public static CubeArcDifficulty ForLevel(int level)
    {
        switch (level)
        {
            case 2:
                return new CubeArcDifficulty { radius = 0.25f, centerDistance = 0.30f, corridorHalfWidth = 0.04f, showGhost = true, visibleAhead = 1f };
            case 3:
                return new CubeArcDifficulty { radius = 0.25f, centerDistance = 0.30f, corridorHalfWidth = 0.03f, showGhost = false, visibleAhead = 0.34f };
            default:
                return new CubeArcDifficulty { radius = 0.20f, centerDistance = 0.30f, corridorHalfWidth = 0.06f, showGhost = true, visibleAhead = 1f };
        }
    }
}
