using App.Models;
using Newtonsoft.Json;
using UnityEngine;

/// <summary>
/// Vstupní bod hry "Přenášení kostky po oblouku" (gameId "cube_arc") pro MinigameController.
/// Vybere zdroj pózy kostky (AprilTag z kamery, v Editoru ovladač) a spustí úroveň podle obtížnosti.
/// </summary>
public class MainCubeArcManager : MonoBehaviour, IMiniGame
{
    [Header("Zdroje pózy kostky")]
    [SerializeField] private AprilTagCubeTracker markerTracker;
    [SerializeField] private ControllerCubePoseSource controllerSource;
    [Tooltip("Použít ovladač místo fyzické kostky i na brýlích (testování bez kostky).")]
    [SerializeField] private bool forceControllerSource = false;

    [Header("Vzhled")]
    [Tooltip("Materiál se shaderem CubeArc/UnlitVertexColor.")]
    [SerializeField] private Material visualsMaterial;

    [Header("Ladění")]
    [Tooltip("Zobrazit osy tagů a frekvenci detekce.")]
    [SerializeField] private CubeTrackerDebugOverlay debugOverlay;
    [SerializeField] private bool showTrackingDebug = false;
    [Tooltip("V Editoru spustit hru hned po startu (bez příkazu z asistenční aplikace).")]
    [SerializeField] private bool autoStartInEditor = false;
    [Range(1, 3)] [SerializeField] private int editorDifficulty = 1;

    private CubeArcLevelManager activeLevel;
    private bool started;

    private void Start()
    {
        if (Application.isEditor && autoStartInEditor && !started)
            StartGame(JsonConvert.SerializeObject(new CubeArcConfig { difficulty = editorDifficulty, iterations = 3, start_side = "left" }));
    }

    public void StartGame(string configJson)
    {
        started = true;
        int difficulty = 1;
        int iterations = SessionManager.Instance != null ? SessionManager.Instance.TotalIterations : 1;
        string startSide = "left";

        if (!string.IsNullOrEmpty(configJson))
        {
            try
            {
                var config = JsonConvert.DeserializeObject<CubeArcConfig>(configJson);
                difficulty = Mathf.Clamp(config.difficulty, 1, 3);
                if (config.iterations > 0) iterations = config.iterations;
                if (!string.IsNullOrEmpty(config.start_side)) startSide = config.start_side;
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"[MainCubeArcManager] Chyba v konfiguraci, použiji výchozí: {e.Message}");
            }
        }

        ICubePoseSource source = ChooseSource();
        if (source == null)
        {
            Debug.LogError("[MainCubeArcManager] Není k dispozici sledování kostky (kamera ani ovladač).");
            SessionManager.Instance?.SendSystemStatus("error_tracking", "CubeArc", difficulty, iterations);
            return;
        }

        if (debugOverlay != null) debugOverlay.gameObject.SetActive(showTrackingDebug && source is AprilTagCubeTracker);

        StopGame();
        var levelObject = new GameObject($"CubeArcLevel{difficulty}");
        levelObject.transform.SetParent(transform, false);
        activeLevel = levelObject.AddComponent<CubeArcLevelManager>();
        activeLevel.Begin(source, CubeArcDifficulty.ForLevel(difficulty), difficulty, startSide != "right", iterations, visualsMaterial);

        Debug.Log($"[MainCubeArcManager] Level {difficulty}, {iterations} kol, start {startSide}, zdroj {source.GetType().Name}");
    }

    public void StopGame()
    {
        if (activeLevel != null)
        {
            Destroy(activeLevel.gameObject);
            activeLevel = null;
        }
    }

    private ICubePoseSource ChooseSource()
    {
        bool useController = forceControllerSource || Application.isEditor
                             || markerTracker == null || !markerTracker.IsAvailable;

        if (!useController)
        {
            if (controllerSource != null) controllerSource.enabled = false;
            markerTracker.enabled = true;
            return markerTracker;
        }

        // Kamera se nepoužije: tracker vypneme, ať zbytečně nestahuje obraz.
        if (markerTracker != null) markerTracker.enabled = false;
        if (controllerSource != null && controllerSource.IsAvailable)
        {
            controllerSource.enabled = true;
            return controllerSource;
        }
        return null;
    }
}
