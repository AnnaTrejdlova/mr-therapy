using System.Collections.Generic;
using UnityEngine;

namespace CubeArc
{
    /// <summary>
    /// Rozhoduje, zda pacient kostku drží jednou rukou, a když se kostka krátce ztratí z kamery
    /// (zakryje ji ruka), dopočítá její pózu z pózy ruky.
    ///
    /// Kostka "drží v ruce", pokud v posledním okně (~0,35 s) viditelnosti:
    ///  - byla ruka blízko kostky (zápěstí do HoldRadius),
    ///  - poloha kostky vůči ruce se skoro neměnila (pohybují se spolu),
    ///  - a kostka se opravdu pohnula (aby ruka jen držená nad ležící kostkou s ní pak "neodjela").
    /// Když se pak kostka ztratí, jede s rukou s posledním naměřeným posunem, nejdéle MaxBridgeDuration.
    /// </summary>
    public class HandGrip
    {
        public float HoldRadius = 0.15f;        // m, zápěstí ↔ střed kostky
        public float MaxOffsetDrift = 0.025f;   // m, jak moc se smí změnit poloha kostky vůči ruce
        public float MinTravel = 0.015f;        // m, kostka se musí v okně pohnout aspoň o tolik
        public float Window = 0.35f;            // s
        public float MaxBridgeDuration = 3f;    // s, delší výpadek už rukou nepřemosťujeme

        private struct Sample
        {
            public float Time;
            public Vector3 CubeWorld;
            public Vector3 LocalPosition;     // střed kostky v souřadnicích ruky
            public Quaternion LocalRotation;  // natočení kostky v souřadnicích ruky
        }

        private readonly List<Sample> history = new List<Sample>();
        private float lastCubeTime = float.NegativeInfinity;

        /// <summary>Ruka kostku drží (podle posledních měření, kdy byla kostka vidět).</summary>
        public bool IsHolding { get; private set; }

        /// <summary>Vzdálenost zápěstí od kostky při posledním měření [m] (pro výběr ruky).</summary>
        public float LastDistance { get; private set; } = float.PositiveInfinity;

        /// <summary>Zavolat, když je kostka vidět (každé nové měření z kamery).</summary>
        public void ObserveCube(float time, Pose cube, bool handTracked, Pose hand)
        {
            lastCubeTime = time;
            if (!handTracked)
            {
                history.Clear();
                IsHolding = false;
                LastDistance = float.PositiveInfinity;
                return;
            }

            Quaternion inverse = Quaternion.Inverse(hand.rotation);
            history.Add(new Sample
            {
                Time = time,
                CubeWorld = cube.position,
                LocalPosition = inverse * (cube.position - hand.position),
                LocalRotation = inverse * cube.rotation
            });
            while (history.Count > 0 && history[0].Time < time - Window) history.RemoveAt(0);

            LastDistance = Vector3.Distance(cube.position, hand.position);
            IsHolding = EvaluateHolding();
        }

        /// <summary>
        /// Když kostka není vidět: vrátí true a odhad pózy kostky, pokud ji ruka držela,
        /// ruka je sledovaná a výpadek není moc dlouhý.
        /// </summary>
        public bool TryBridge(float time, bool handTracked, Pose hand, out Pose cube)
        {
            cube = default;
            if (!IsHolding || !handTracked || history.Count == 0) return false;
            if (time - lastCubeTime > MaxBridgeDuration) return false;

            Sample last = history[history.Count - 1];
            cube = new Pose(hand.position + hand.rotation * last.LocalPosition, hand.rotation * last.LocalRotation);
            return true;
        }

        public void Reset()
        {
            history.Clear();
            IsHolding = false;
            LastDistance = float.PositiveInfinity;
            lastCubeTime = float.NegativeInfinity;
        }

        private bool EvaluateHolding()
        {
            if (history.Count < 3) return false;
            Sample last = history[history.Count - 1];
            if (last.Time - history[0].Time < Window * 0.5f) return false; // málo dlouhá historie
            if (LastDistance > HoldRadius) return false;

            float travel = 0f;
            foreach (Sample s in history)
            {
                if (Vector3.Distance(s.LocalPosition, last.LocalPosition) > MaxOffsetDrift) return false;
                travel = Mathf.Max(travel, Vector3.Distance(s.CubeWorld, last.CubeWorld));
            }
            return travel >= MinTravel;
        }
    }
}
