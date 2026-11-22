using System;
using System.Collections.Generic;
using UnityEngine;

namespace CubeArc
{
    /// <summary>Souhrn jednoho kola (přenesení kostky po oblouku), posílá se v události Trial_Complete.</summary>
    [Serializable]
    public class TrialSummary
    {
        public float duration_s;
        public float path_length_m;
        public float arc_length_m;
        public float path_ratio;
        public float mean_dev_cm;
        public float max_dev_cm;
        public float time_outside_corridor_s;
        public int corridor_exits;
        public float max_height_cm;
        public int stops;
        public float tracking_lost_s;
        public float max_progress;
        /// <summary>Průměrná odchylka kolmo na rovinu oblouku [cm], + od pacienta (drift dopředu/dozadu).</summary>
        public float mean_depth_cm;
        /// <summary>Vzorky 10 Hz: [čas s, x m (doprava), y m (nahoru), z m (od pacienta)], vůči středu základny oblouku.</summary>
        public List<float[]> samples;
    }

    /// <summary>
    /// Sbírá průběh jednoho kola a počítá metriky. Čistá logika bez MonoBehaviour, aby šla testovat.
    /// </summary>
    public class TrialRecorder
    {
        public const float SampleInterval = 0.1f;
        public const float StopSpeed = 0.02f;      // m/s – pod touto rychlostí kostka "stojí"
        public const float StopMinDuration = 0.3f; // s – jak dlouho musí stát, aby to byla zastávka

        private readonly ArcPath arc;
        private readonly float corridorHalfWidth;
        private readonly float startTime;

        private float lastTime;
        private bool hasLastPosition;
        private Vector3 lastPosition;

        private float pathLength;
        private float deviationTimeSum;
        private float depthTimeSum;
        private float trackedTime;
        private float maxDeviation;
        private float timeOutside;
        private int exits;
        private bool wasInside = true;
        private float maxHeight;
        private float lostTime;
        private float maxProgress;

        private float stillTime;
        private bool countedThisStop;
        private int stops;

        private float nextSampleTime;
        private readonly List<float[]> samples = new List<float[]>();

        public TrialRecorder(ArcPath arc, float corridorHalfWidth, float startTime)
        {
            this.arc = arc;
            this.corridorHalfWidth = corridorHalfWidth;
            this.startTime = startTime;
            lastTime = startTime;
            nextSampleTime = startTime;
        }

        /// <summary>Nejdál dosažená poloha na oblouku (0..1), nikdy neklesá.</summary>
        public float MaxProgress => maxProgress;
        public bool IsInsideCorridor => wasInside;
        public float Elapsed => lastTime - startTime;

        /// <summary>Zavolat každý snímek.</summary>
        /// <param name="tracked">Zda je kostka právě viditelná.</param>
        /// <param name="position">Střed kostky ve světě (ignoruje se, když není vidět).</param>
        public void Tick(float time, bool tracked, Vector3 position)
        {
            float dt = Mathf.Max(0f, time - lastTime);
            lastTime = time;

            if (!tracked)
            {
                lostTime += dt;
                hasLastPosition = false; // dráhu přes výpadek nepočítáme
                return;
            }

            ArcProjection p = arc.Project(position);
            float height = Mathf.Max(0f, p.Height); // zvednutí nad polohu na stole

            if (hasLastPosition)
            {
                float step = Vector3.Distance(position, lastPosition);
                pathLength += step;

                float speed = dt > 1e-5f ? step / dt : 0f;
                bool moving = speed >= StopSpeed;
                bool midway = maxProgress > 0.05f && maxProgress < 0.95f;
                if (!moving && midway)
                {
                    stillTime += dt;
                    if (stillTime >= StopMinDuration && !countedThisStop)
                    {
                        stops++;
                        countedThisStop = true;
                    }
                }
                else if (moving)
                {
                    stillTime = 0f;
                    countedThisStop = false;
                }
            }

            trackedTime += dt;
            deviationTimeSum += p.Deviation * dt;
            depthTimeSum += p.Depth * dt;
            maxDeviation = Mathf.Max(maxDeviation, p.Deviation);
            maxHeight = Mathf.Max(maxHeight, height);
            maxProgress = Mathf.Max(maxProgress, p.T);

            bool inside = p.Deviation <= corridorHalfWidth;
            if (!inside) timeOutside += dt;
            if (wasInside && !inside) exits++;
            wasInside = inside;

            if (time >= nextSampleTime)
            {
                Vector3 local = arc.ToLocal(position);
                samples.Add(new[]
                {
                    Round(time - startTime, 100f), Round(local.x, 1000f), Round(local.y, 1000f), Round(local.z, 1000f)
                });
                // Pevná mřížka 10 Hz, aby se interval neprodlužoval o zbytek snímku.
                while (nextSampleTime <= time) nextSampleTime += SampleInterval;
            }

            lastPosition = position;
            hasLastPosition = true;
        }

        public TrialSummary BuildSummary()
        {
            float arcLength = arc.Length;
            return new TrialSummary
            {
                duration_s = Round(lastTime - startTime, 100f),
                path_length_m = Round(pathLength, 1000f),
                arc_length_m = Round(arcLength, 1000f),
                path_ratio = arcLength > 0f ? Round(pathLength / arcLength, 100f) : 0f,
                mean_dev_cm = trackedTime > 0f ? Round(deviationTimeSum / trackedTime * 100f, 10f) : 0f,
                max_dev_cm = Round(maxDeviation * 100f, 10f),
                time_outside_corridor_s = Round(timeOutside, 100f),
                corridor_exits = exits,
                max_height_cm = Round(maxHeight * 100f, 10f),
                stops = stops,
                tracking_lost_s = Round(lostTime, 100f),
                max_progress = Round(maxProgress, 100f),
                mean_depth_cm = trackedTime > 0f ? Round(depthTimeSum / trackedTime * 100f, 10f) : 0f,
                samples = new List<float[]>(samples)
            };
        }

        private static float Round(float value, float factor) => Mathf.Round(value * factor) / factor;
    }
}
