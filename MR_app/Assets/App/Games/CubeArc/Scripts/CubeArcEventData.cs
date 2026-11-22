using CubeArc;

/// <summary>
/// Telemetrická událost hry CubeArc (posílá se přes SessionManager.SendLog).
/// Události: Setup_Table, Trial_Start, Corridor_Exit, Corridor_Enter, Cube_Lost, Cube_Found, Trial_Complete.
/// </summary>
[System.Serializable]
public class CubeArcEventData
{
    public string event_type;
    public string details;
    public int iteration;
    public float time_since_start;
    public int difficulty;
    public string start_side;
    /// <summary>Vyplněno jen u Trial_Complete.</summary>
    public TrialSummary summary;
}
